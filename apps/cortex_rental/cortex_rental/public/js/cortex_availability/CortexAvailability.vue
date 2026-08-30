<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";

// ---------------------------------------------------------------------
// Constants — mirrors cortex_rental_item_profile.json's `category`
// Select options and the rental_state values on Cortex Rental
// Transaction. Kept in sync by hand for now (no endpoint exposes
// DocType meta to this page yet); a drift here is cosmetic (a filter
// option would just never match anything), not a security or data
// issue, so it's an accepted simplification for this first pass.
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

const STATE_META = {
	Quote: { label: "Soumission", color: "#94a3b8" }, // gray — non-blocking
	Reservation: { label: "Réservation", color: "#f59e0b" }, // amber — blocking, unconfirmed
	Contract: { label: "Contrat", color: "#2563eb" }, // blue — confirmed
	"Checked Out": { label: "Sorti", color: "#7c3aed" }, // violet — equipment out
};
const STATE_ORDER = ["Quote", "Reservation", "Contract", "Checked Out"];

const VIEW_DAYS = { day: 1, week: 7, month: 30 };

// ---------------------------------------------------------------------
// State
// ---------------------------------------------------------------------
const viewMode = ref("week");
const refDate = ref(startOfWeek(new Date()));
const search = ref("");
const activeCategories = reactive(new Set());
const activeStates = reactive(new Set(STATE_ORDER));
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
	const meta = STATE_META[block.rental_state] || { color: "#64748b" };
	return {
		left: `${left}px`,
		width: `${width}px`,
		top: `${block._lane * LANE_HEIGHT + 4}px`,
		background: meta.color,
	};
}

function stateLabel(state) {
	return (STATE_META[state] || {}).label || state;
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
	<div class="cx-app" :class="{ 'cx-sidebar-collapsed': sidebarCollapsed }">
		<header class="cx-toolbar">
			<div class="cx-toolbar-left">
				<h2 class="cx-title">Disponibilité</h2>
				<span class="cx-range-label">{{ rangeLabel }}</span>
			</div>
			<div class="cx-toolbar-right">
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
				<button class="cx-btn cx-btn-primary" @click="createDraft">+ Créer une soumission</button>
			</div>
		</header>

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
						<label v-for="state in STATE_ORDER" :key="state" class="cx-check">
							<input
								type="checkbox"
								:checked="activeStates.has(state)"
								@change="toggleState(state)"
							/>
							<span class="cx-dot" :style="{ background: STATE_META[state].color }"></span>
							<span>{{ STATE_META[state].label }}</span>
						</label>
					</section>
				</div>
			</aside>

			<main class="cx-grid-wrap">
				<div v-if="loading" class="cx-state-panel">
					<div class="cx-skeleton" v-for="n in 6" :key="n"></div>
				</div>

				<div v-else-if="error" class="cx-state-panel cx-error">
					<p>{{ error }}</p>
					<button class="cx-btn" @click="fetchMatrix">Réessayer</button>
				</div>

				<div v-else-if="!filteredItems.length" class="cx-state-panel cx-empty">
					<p>Aucun équipement ne correspond à ces filtres pour cette période.</p>
				</div>

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
							<span v-if="item.has_conflict" class="cx-conflict-badge" title="Conflit potentiel détecté">
								conflit
							</span>
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
			<span v-for="state in STATE_ORDER" :key="state" class="cx-legend-item">
				<span class="cx-dot" :style="{ background: STATE_META[state].color }"></span>
				{{ STATE_META[state].label }}
			</span>
			<span class="cx-legend-item">
				<span class="cx-dot" style="background: #dc2626"></span>
				Conflit
			</span>
		</footer>
	</div>
</template>

<style scoped>
.cx-app {
	display: flex;
	flex-direction: column;
	height: calc(100vh - var(--navbar-height, 56px) - 40px);
	font-size: 13px;
	color: var(--text-color, #1f2937);
}

.cx-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 10px 16px;
	border-bottom: 1px solid var(--border-color, #e5e7eb);
	flex-wrap: wrap;
	gap: 10px;
}
.cx-toolbar-left {
	display: flex;
	align-items: baseline;
	gap: 10px;
}
.cx-title {
	margin: 0;
	font-size: 16px;
	font-weight: 600;
}
.cx-range-label {
	color: var(--text-muted, #6b7280);
	font-variant-numeric: tabular-nums;
}
.cx-toolbar-right {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}
.cx-nav-group,
.cx-view-toggle {
	display: inline-flex;
	border: 1px solid var(--border-color, #e5e7eb);
	border-radius: 6px;
	overflow: hidden;
}
.cx-btn {
	border: none;
	background: var(--control-bg, #fff);
	padding: 5px 10px;
	cursor: pointer;
	font-size: 12.5px;
	color: inherit;
}
.cx-btn + .cx-btn {
	border-left: 1px solid var(--border-color, #e5e7eb);
}
.cx-btn:hover {
	background: var(--control-bg-on-gray, #f3f4f6);
}
.cx-btn-active {
	background: #4f46e5;
	color: #fff;
}
.cx-btn-icon {
	width: 28px;
	font-weight: 700;
}
.cx-btn-primary {
	background: #4f46e5;
	color: #fff;
	border-radius: 6px;
	padding: 6px 12px;
	font-weight: 600;
}
.cx-btn-primary:hover {
	background: #4338ca;
}
.cx-search {
	border: 1px solid var(--border-color, #e5e7eb);
	border-radius: 6px;
	padding: 5px 10px;
	min-width: 220px;
	font-size: 12.5px;
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
	border-right: 1px solid var(--border-color, #e5e7eb);
	transition: width 0.22s ease;
	overflow: hidden;
}
.cx-sidebar-collapsed .cx-sidebar {
	width: 16px;
}
.cx-sidebar-content {
	width: 220px;
	padding: 14px 12px;
	opacity: 1;
	transition: opacity 0.15s ease;
	overflow-y: auto;
	height: 100%;
}
.cx-sidebar-collapsed .cx-sidebar-content {
	opacity: 0;
	pointer-events: none;
}
.cx-sidebar-toggle {
	position: absolute;
	top: 8px;
	right: -2px;
	width: 18px;
	height: 18px;
	border-radius: 50%;
	border: 1px solid var(--border-color, #e5e7eb);
	background: var(--control-bg, #fff);
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
	margin-bottom: 18px;
}
.cx-filter-group h4 {
	margin: 0 0 8px;
	font-size: 11px;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--text-muted, #6b7280);
}
.cx-check {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 3px 0;
	cursor: pointer;
}
.cx-hint {
	font-size: 11px;
	color: var(--text-muted, #9ca3af);
	margin: 4px 0 0;
}

.cx-grid-wrap {
	flex: 1;
	overflow: auto;
	position: relative;
}

.cx-state-panel {
	padding: 40px 24px;
	text-align: center;
	color: var(--text-muted, #6b7280);
}
.cx-skeleton {
	height: 32px;
	border-radius: 6px;
	margin-bottom: 8px;
	background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 37%, #f3f4f6 63%);
	background-size: 400% 100%;
	animation: cx-shimmer 1.4s ease infinite;
}
@keyframes cx-shimmer {
	0% {
		background-position: 100% 50%;
	}
	100% {
		background-position: 0 50%;
	}
}
.cx-error {
	color: #b91c1c;
}

.cx-grid {
	display: table;
	min-width: 100%;
}
.cx-grid-header {
	display: flex;
	position: sticky;
	top: 0;
	background: var(--fg-color, #fff);
	z-index: 3;
	border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.cx-corner {
	width: 220px;
	flex-shrink: 0;
	position: sticky;
	left: 0;
	background: var(--fg-color, #fff);
	z-index: 4;
}
.cx-header-cols {
	display: flex;
}
.cx-header-cell {
	flex-shrink: 0;
	padding: 8px 6px;
	font-size: 11px;
	text-align: center;
	color: var(--text-muted, #6b7280);
	border-left: 1px solid var(--border-color, #f3f4f6);
}

.cx-grid-row {
	display: flex;
	border-bottom: 1px solid var(--border-color, #f3f4f6);
}
.cx-row-label {
	width: 220px;
	flex-shrink: 0;
	position: sticky;
	left: 0;
	background: var(--fg-color, #fff);
	z-index: 2;
	padding: 8px 10px;
	display: flex;
	flex-direction: column;
	gap: 2px;
	border-right: 1px solid var(--border-color, #e5e7eb);
}
.cx-item-name {
	font-weight: 600;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.cx-item-fleet {
	font-size: 11px;
	color: var(--text-muted, #6b7280);
}
.cx-conflict-badge {
	font-size: 10.5px;
	font-weight: 600;
	color: #b91c1c;
	background: #fee2e2;
	border-radius: 4px;
	padding: 1px 6px;
	width: fit-content;
}

.cx-row-track {
	position: relative;
}
.cx-cell-bg {
	position: absolute;
	top: 0;
	bottom: 0;
	border-left: 1px solid var(--border-color, #f3f4f6);
}
.cx-block {
	position: absolute;
	border-radius: 5px;
	color: #fff;
	font-size: 11px;
	font-weight: 600;
	padding: 4px 8px;
	height: 24px;
	display: flex;
	align-items: center;
	cursor: pointer;
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
}
.cx-block:hover {
	filter: brightness(0.92);
}

.cx-legend {
	display: flex;
	gap: 18px;
	padding: 8px 16px;
	border-top: 1px solid var(--border-color, #e5e7eb);
	font-size: 11.5px;
	color: var(--text-muted, #6b7280);
	flex-wrap: wrap;
}
.cx-legend-item {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.cx-dot {
	width: 9px;
	height: 9px;
	border-radius: 50%;
	display: inline-block;
	flex-shrink: 0;
}
</style>
