<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { STATE_META, stateKeyForRentalState } from "../cortex_shared/stateMeta.js";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexStatusBadge from "../cortex_shared/CortexStatusBadge.vue";
import CortexLoadingState from "../cortex_shared/CortexLoadingState.vue";
import CortexErrorState from "../cortex_shared/CortexErrorState.vue";
import CortexEmptyState from "../cortex_shared/CortexEmptyState.vue";

// ---------------------------------------------------------------------
// Constants — mirrors cortex_rental_item_profile.json's `category`
// Select options. Kept in sync by hand for now (no endpoint exposes
// DocType meta to this page yet); a drift here is cosmetic (a filter
// option would just never match anything), not a security or data
// issue, so it's an accepted simplification for this first pass.
//
// The transaction states themselves come from cortex_shared/stateMeta.js
// (STATE_META) — single source of truth shared with every other Cortex
// page, not redefined here (see docs/design-system.md).
// ---------------------------------------------------------------------
const CATEGORIES = [
	"Camera Bodies",
	"Cinema Lenses",
	"Lighting",
	"Grip & Rigging",
	"Audio",
	"Monitors & Wireless Video",
	"Power & Batteries",
];

// This grid only ever shows the states get_matrix can return (see
// api/v1/availability.py's ALL_MATRIX_STATES) — a subset of the full
// STATE_META key set (which also covers Returned/Closed/Disputed/etc.
// for other screens). Raw values match `rental_state` exactly, as
// returned by the API; token keys (right-hand side) are what
// stateMeta.js indexes STATE_META/BLOCK_FILL_VAR by.
const GRID_RENTAL_STATES = ["Quote", "Reservation", "Contract", "Checked Out"];

// Solid ("plein", per the design spec) fill for the calendar bars —
// deliberately more saturated than the pale badge backgrounds
// (--state-*-bg) used elsewhere, matching "Reservation : ambre plein.
// Contract : bleu plein." in docs/design-system.md's Disponibilité
// section. Reuses the same base palette tokens rather than inventing a
// third color per state.
const BLOCK_FILL_VAR = {
	quote: "var(--cortex-border-strong)",
	reservation: "var(--cortex-warning-500)",
	contract: "var(--cortex-info-600)",
	checked_out: "var(--cortex-violet-600)",
};

const VIEW_DAYS = { day: 1, week: 7, month: 30 };

// ---------------------------------------------------------------------
// State
// ---------------------------------------------------------------------
const viewMode = ref("week");
const refDate = ref(startOfWeek(new Date()));
const search = ref("");
const activeCategories = reactive(new Set());
const activeStates = reactive(new Set(GRID_RENTAL_STATES));
const sidebarCollapsed = ref(false);

const loading = ref(true);
const error = ref("");
const items = ref([]);
const resolvedCompany = ref("");

let searchDebounce = null;

// ---------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------
function startOfWeek(d) {
	const date = new Date(d);
	const day = (date.getDay() + 6) % 7; // Monday = 0
	date.setDate(date.getDate() - day);
	date.setHours(0, 0, 0, 0);
	return date;
}

function addDays(d, n) {
	const date = new Date(d);
	date.setDate(date.getDate() + n);
	return date;
}

function fmtDateTime(d) {
	const pad = (n) => String(n).padStart(2, "0");
	return (
		`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
		`${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
	);
}

function fmtDateShort(d) {
	return d.toLocaleDateString("fr-CA", { weekday: "short", day: "2-digit", month: "2-digit" });
}

// ---------------------------------------------------------------------
// Columns for the current view
// ---------------------------------------------------------------------
const columns = computed(() => {
	const n = VIEW_DAYS[viewMode.value];
	const cols = [];
	for (let i = 0; i < n; i++) cols.push(addDays(refDate.value, i));
	return cols;
});

const rangeStart = computed(() => columns.value[0]);
const rangeEnd = computed(() => addDays(columns.value[columns.value.length - 1], 1));

const cellWidth = computed(() => (viewMode.value === "month" ? 44 : viewMode.value === "day" ? 320 : 108));

const rangeLabel = computed(() => {
	const start = rangeStart.value;
	const end = addDays(rangeEnd.value, -1);
	const fmt = (d) => d.toLocaleDateString("fr-CA", { day: "2-digit", month: "short", year: "numeric" });
	return viewMode.value === "day" ? fmt(start) : `${fmt(start)} — ${fmt(end)}`;
});

// ---------------------------------------------------------------------
// Data fetch
// ---------------------------------------------------------------------
function fetchMatrix() {
	loading.value = true;
	error.value = "";

	const args = {
		starts_at: fmtDateTime(rangeStart.value),
		ends_at: fmtDateTime(rangeEnd.value),
	};
	if (search.value.trim()) args.search = search.value.trim();

	frappe.call({
		method: "cortex_rental.api.v1.availability.get_matrix",
		type: "GET",
		args,
		callback(r) {
			loading.value = false;
			const data = (r.message && r.message.data) || { items: [] };
			items.value = data.items || [];
			resolvedCompany.value = (r.message && r.message.meta && r.message.meta.company) || "";
			if (!activeCategories.size) {
				// First load: default to "all categories" — represented as an
				// empty active set meaning "no category filter applied" below.
			}
		},
		error(r) {
			loading.value = false;
			error.value =
				(r && r.responseJSON && (r.responseJSON.message || r.responseJSON.exc)) ||
				"Impossible de charger la disponibilité. Vérifiez la connexion au serveur.";
		},
	});
}

watch([viewMode, refDate], fetchMatrix);
watch(search, () => {
	clearTimeout(searchDebounce);
	searchDebounce = setTimeout(fetchMatrix, 350);
});
onMounted(fetchMatrix);

// ---------------------------------------------------------------------
// Filtering + lane layout (stacks overlapping blocks within a row so
// two Quotes on the same item/window don't visually collide)
// ---------------------------------------------------------------------
const filteredItems = computed(() => {
	return items.value
		.filter((it) => !activeCategories.size || activeCategories.has(it.category))
		.map((it) => {
			const blocks = (it.blocks || []).filter((b) => activeStates.has(b.rental_state));
			return { ...it, _lanes: layoutLanes(blocks) };
		});
});

function layoutLanes(blocks) {
	const sorted = [...blocks].sort((a, b) => new Date(a.starts_at) - new Date(b.starts_at));
	const lanes = []; // each lane: last block end (Date)
	const placed = [];
	for (const b of sorted) {
		const start = new Date(b.starts_at);
		const end = new Date(b.ends_at);
		let laneIndex = lanes.findIndex((laneEnd) => laneEnd <= start);
		if (laneIndex === -1) {
			laneIndex = lanes.length;
			lanes.push(end);
		} else {
			lanes[laneIndex] = end;
		}
		placed.push({ ...b, _lane: laneIndex, _start: start, _end: end });
	}
	return { blocks: placed, laneCount: Math.max(1, lanes.length) };
}

const LANE_HEIGHT = 30;
const ROW_PADDING = 10;

function rowHeight(item) {
	return item._lanes.laneCount * LANE_HEIGHT + ROW_PADDING;
}

function blockStyle(block) {
	const dayMs = 24 * 60 * 60 * 1000;
	const offsetDays = Math.max(0, (block._start - rangeStart.value) / dayMs);
	const endOffsetDays = Math.min(columns.value.length, (block._end - rangeStart.value) / dayMs);
	const left = offsetDays * cellWidth.value;
	const width = Math.max(cellWidth.value * 0.4, (endOffsetDays - offsetDays) * cellWidth.value - 4);
	const stateKey = stateKeyForRentalState(block.rental_state);
	return {
		left: `${left}px`,
		width: `${width}px`,
		top: `${block._lane * LANE_HEIGHT + 4}px`,
		background: BLOCK_FILL_VAR[stateKey] || "var(--cortex-text-disabled)",
	};
}

function stateLabel(rentalState) {
	const key = stateKeyForRentalState(rentalState);
	return (STATE_META[key] || {}).label || rentalState;
}

function toggleCategory(cat) {
	if (activeCategories.has(cat)) activeCategories.delete(cat);
	else activeCategories.add(cat);
}

function toggleState(state) {
	if (activeStates.has(state)) activeStates.delete(state);
	else activeStates.add(state);
}

// ---------------------------------------------------------------------
// Actions — real Frappe navigation, not decorative links
// ---------------------------------------------------------------------
function openTransaction(block) {
	frappe.set_route("Form", "Cortex Rental Transaction", block.transaction);
}

function createDraft() {
	// Prefills dates + the server-resolved Company. Equipment lines still
	// need to be added manually on the transaction form — prefilling a
	// child table row from a query param is a real follow-up, not faked
	// here.
	frappe.new_doc("Cortex Rental Transaction", {
		starts_at: fmtDateTime(rangeStart.value),
		ends_at: fmtDateTime(addDays(rangeStart.value, 1)),
		company: resolvedCompany.value || undefined,
	});
}

function shiftRange(delta) {
	const days = VIEW_DAYS[viewMode.value];
	refDate.value = addDays(refDate.value, days * delta);
}

function goToday() {
	refDate.value = viewMode.value === "week" ? startOfWeek(new Date()) : new Date(new Date().setHours(0, 0, 0, 0));
}
</script>

<template>
	<div class="cortex-app cx-app" :class="{ 'cx-sidebar-collapsed': sidebarCollapsed }">
		<CortexPageHeader title="Disponibilité" :subtitle="rangeLabel">
			<template #secondary>
				<div class="cx-nav-group">
					<button class="cx-btn cx-btn-icon" @click="shiftRange(-1)" title="Période précédente">‹</button>
					<button class="cx-btn" @click="goToday">Aujourd'hui</button>
					<button class="cx-btn cx-btn-icon" @click="shiftRange(1)" title="Période suivante">›</button>
				</div>
				<div class="cx-view-toggle">
					<button
						v-for="mode in ['day', 'week', 'month']"
						:key="mode"
						class="cx-btn"
						:class="{ 'cx-btn-active': viewMode === mode }"
						@click="viewMode = mode"
					>
						{{ mode === "day" ? "Jour" : mode === "week" ? "Semaine" : "Mois" }}
					</button>
				</div>
				<input
					v-model="search"
					class="cx-search"
					type="search"
					placeholder="Rechercher un équipement…"
					aria-label="Rechercher un équipement"
				/>
			</template>
			<template #primary>
				<button class="cx-btn cx-btn-primary" @click="createDraft">+ Créer une soumission</button>
			</template>
		</CortexPageHeader>

		<div class="cx-body">
			<aside class="cx-sidebar">
				<button
					class="cx-sidebar-toggle"
					@click="sidebarCollapsed = !sidebarCollapsed"
					:title="sidebarCollapsed ? 'Ouvrir les filtres' : 'Réduire les filtres'"
				>
					<span :class="{ 'cx-flip': sidebarCollapsed }">‹</span>
				</button>
				<div class="cx-sidebar-content">
					<section class="cx-filter-group">
						<h4>Catégorie</h4>
						<label v-for="cat in CATEGORIES" :key="cat" class="cx-check">
							<input
								type="checkbox"
								:checked="activeCategories.has(cat)"
								@change="toggleCategory(cat)"
							/>
							<span>{{ cat }}</span>
						</label>
						<p v-if="!activeCategories.size" class="cx-hint">Aucun filtre = toutes les catégories</p>
					</section>
					<section class="cx-filter-group">
						<h4>État</h4>
						<label v-for="state in GRID_RENTAL_STATES" :key="state" class="cx-check">
							<input
								type="checkbox"
								:checked="activeStates.has(state)"
								@change="toggleState(state)"
							/>
							<span
								class="cx-dot"
								:style="{ background: BLOCK_FILL_VAR[stateKeyForRentalState(state)] }"
							></span>
							<span>{{ stateLabel(state) }}</span>
						</label>
					</section>
				</div>
			</aside>

			<main class="cx-grid-wrap">
				<div v-if="loading" style="padding: var(--space-4)">
					<CortexLoadingState :rows="6" :row-height="32" />
				</div>

				<div v-else-if="error" style="padding: var(--space-4)">
					<CortexErrorState
						:message="error"
						consequence="Aucune réservation n'a été créée."
						@retry="fetchMatrix"
					/>
				</div>

				<CortexEmptyState
					v-else-if="!filteredItems.length"
					message="Aucun équipement ne correspond à ces filtres pour cette période."
				/>

				<div v-else class="cx-grid" :style="{ '--cell-w': cellWidth + 'px', '--col-count': columns.length }">
					<div class="cx-grid-header">
						<div class="cx-corner"></div>
						<div class="cx-header-cols">
							<div
								v-for="(col, i) in columns"
								:key="i"
								class="cx-header-cell"
								:style="{ width: cellWidth + 'px' }"
							>
								{{ fmtDateShort(col) }}
							</div>
						</div>
					</div>

					<div class="cx-grid-row" v-for="item in filteredItems" :key="item.item_code">
						<div class="cx-row-label" :title="item.item_code">
							<span class="cx-item-name">{{ item.item_name || item.item_code }}</span>
							<span class="cx-item-fleet">{{ item.fleet_quantity }} unités</span>
							<CortexStatusBadge v-if="item.has_conflict" state="conflict" tooltip="Conflit potentiel détecté" />
						</div>
						<div
							class="cx-row-track"
							:style="{ height: rowHeight(item) + 'px', width: cellWidth * columns.length + 'px' }"
						>
							<div
								v-for="(col, i) in columns"
								:key="i"
								class="cx-cell-bg"
								:style="{ width: cellWidth + 'px', left: i * cellWidth + 'px' }"
							></div>
							<div
								v-for="block in item._lanes.blocks"
								:key="block.transaction"
								class="cx-block"
								:style="blockStyle(block)"
								:title="`${block.transaction} · ${block.customer} · ${stateLabel(block.rental_state)}`"
								@click="openTransaction(block)"
							>
								<span class="cx-block-label"
									>{{ block.customer }} · {{ stateLabel(block.rental_state) }}</span
								>
							</div>
						</div>
					</div>
				</div>
			</main>
		</div>

		<footer class="cx-legend">
			<span v-for="state in GRID_RENTAL_STATES" :key="state" class="cx-legend-item">
				<span class="cx-dot" :style="{ background: BLOCK_FILL_VAR[stateKeyForRentalState(state)] }"></span>
				{{ stateLabel(state) }}
			</span>
			<CortexStatusBadge state="conflict" />
		</footer>
	</div>
</template>

<style scoped>
/* Buttons (.cx-btn / .cx-btn-primary) and the loading skeleton shimmer
   come from cortex-utilities.css now — not redefined here (see
   docs/design-system.md "Conventions d'intégration"). Everything below
   is layout specific to this page's calendar grid. */

.cx-app {
	display: flex;
	flex-direction: column;
	height: calc(100vh - var(--navbar-height, 56px) - 40px);
	font-size: 13px;
}

.cx-nav-group,
.cx-view-toggle {
	display: inline-flex;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	overflow: hidden;
}
.cx-nav-group .cx-btn,
.cx-view-toggle .cx-btn {
	border-radius: 0;
}
.cx-btn-icon {
	width: 28px;
	font-weight: 700;
}
.cx-search {
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: 5px var(--space-3);
	min-width: 220px;
	font-size: 12.5px;
	font-family: inherit;
}

.cx-body {
	display: flex;
	flex: 1;
	min-height: 0;
}

/* --- Sidebar with a real width/opacity transition, not a hard toggle --- */
.cx-sidebar {
	position: relative;
	width: 220px;
	flex-shrink: 0;
	border-right: 1px solid var(--cortex-border);
	transition: width var(--motion-base);
	overflow: hidden;
}
.cx-sidebar-collapsed .cx-sidebar {
	width: 16px;
}
.cx-sidebar-content {
	width: 220px;
	padding: var(--space-4) var(--space-3);
	opacity: 1;
	transition: opacity var(--motion-fast);
	overflow-y: auto;
	height: 100%;
}
.cx-sidebar-collapsed .cx-sidebar-content {
	opacity: 0;
	pointer-events: none;
}
.cx-sidebar-toggle {
	position: absolute;
	top: var(--space-2);
	right: -2px;
	width: 18px;
	height: 18px;
	border-radius: 50%;
	border: 1px solid var(--cortex-border);
	background: var(--cortex-surface);
	cursor: pointer;
	z-index: 2;
	font-size: 11px;
	line-height: 1;
	display: flex;
	align-items: center;
	justify-content: center;
}
.cx-sidebar-toggle .cx-flip {
	display: inline-block;
	transform: rotate(180deg);
}
.cx-filter-group {
	margin-bottom: var(--space-5);
}
.cx-filter-group h4 {
	margin: 0 0 var(--space-2);
	font-size: 11px;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--cortex-text-secondary);
}
.cx-check {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	padding: 3px 0;
	cursor: pointer;
	font-size: 13px;
}
.cx-hint {
	font-size: 11px;
	color: var(--cortex-text-disabled);
	margin: var(--space-1) 0 0;
}

.cx-grid-wrap {
	flex: 1;
	overflow: auto;
	position: relative;
}

.cx-grid {
	display: table;
	min-width: 100%;
}
.cx-grid-header {
	display: flex;
	position: sticky;
	top: 0;
	background: var(--cortex-surface);
	z-index: 3;
	border-bottom: 1px solid var(--cortex-border);
}
.cx-corner {
	width: 220px;
	flex-shrink: 0;
	position: sticky;
	left: 0;
	background: var(--cortex-surface);
	z-index: 4;
}
.cx-header-cols {
	display: flex;
}
.cx-header-cell {
	flex-shrink: 0;
	padding: var(--space-2) 6px;
	font-size: 11px;
	text-align: center;
	color: var(--cortex-text-muted);
	border-left: 1px solid var(--cortex-surface-subtle);
}

.cx-grid-row {
	display: flex;
	border-bottom: 1px solid var(--cortex-surface-subtle);
}
.cx-row-label {
	width: 220px;
	flex-shrink: 0;
	position: sticky;
	left: 0;
	background: var(--cortex-surface);
	z-index: 2;
	padding: var(--space-2) var(--space-3);
	display: flex;
	flex-direction: column;
	gap: 2px;
	border-right: 1px solid var(--cortex-border);
}
.cx-item-name {
	font-weight: 600;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.cx-item-fleet {
	font-size: 11px;
	color: var(--cortex-text-muted);
}

.cx-row-track {
	position: relative;
}
.cx-cell-bg {
	position: absolute;
	top: 0;
	bottom: 0;
	border-left: 1px solid var(--cortex-surface-subtle);
}
.cx-block {
	position: absolute;
	border-radius: var(--radius-sm);
	color: var(--cortex-inverse);
	font-size: 11px;
	font-weight: 600;
	padding: 4px var(--space-2);
	height: 24px;
	display: flex;
	align-items: center;
	cursor: pointer;
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis;
	box-shadow: var(--shadow-xs);
}
.cx-block:hover {
	filter: brightness(0.92);
}

.cx-legend {
	display: flex;
	gap: var(--space-5);
	padding: var(--space-2) var(--space-4);
	border-top: 1px solid var(--cortex-border);
	font-size: 11.5px;
	color: var(--cortex-text-muted);
	flex-wrap: wrap;
	align-items: center;
}
.cx-legend-item {
	display: inline-flex;
	align-items: center;
	gap: var(--space-2);
}
.cx-dot {
	width: 9px;
	height: 9px;
	border-radius: 50%;
	display: inline-block;
	flex-shrink: 0;
}
</style>
