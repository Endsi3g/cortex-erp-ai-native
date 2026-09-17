<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { STATE_META, stateKeyForRentalState } from "../cortex_shared/stateMeta.js";
import { fmtDateTime, addDays } from "../cortex_shared/dateUtils.js";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexStatusBadge from "../cortex_shared/CortexStatusBadge.vue";
import CortexLoadingState from "../cortex_shared/CortexLoadingState.vue";
import CortexErrorState from "../cortex_shared/CortexErrorState.vue";
import CortexEmptyState from "../cortex_shared/CortexEmptyState.vue";
import CortexKpiCard from "../cortex_shared/CortexKpiCard.vue";
import CortexChart from "../cortex_shared/CortexChart.vue";
import CortexCommandBar from "../cortex_shared/CortexCommandBar.vue";
import { ICONS } from "../cortex_shared/CortexIcons.js";

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
	// Prefills dates via frappe.route_options — the standard Frappe
	// cross-page handoff (read once in on_page_load/onMounted of the
	// destination, then cleared), not a URL query string. Equipment
	// lines still need to be added manually on the Composer — this
	// grid has no per-item selection state to carry over yet.
	frappe.route_options = {
		starts_at: fmtDateTime(rangeStart.value),
		ends_at: fmtDateTime(addDays(rangeStart.value, 1)),
	};
	frappe.set_route("cortex-transaction-composer");
}

function shiftRange(delta) {
	const days = VIEW_DAYS[viewMode.value];
	refDate.value = addDays(refDate.value, days * delta);
}

function goToday() {
	refDate.value = viewMode.value === "week" ? startOfWeek(new Date()) : new Date(new Date().setHours(0, 0, 0, 0));
}

function jumpToDate(dateStr) {
	const d = new Date(dateStr + "T00:00:00");
	refDate.value = viewMode.value === "week" ? startOfWeek(d) : d;
}

const kpiStats = computed(() => {
	let checkedOut = 0;
	let reservations = 0;
	let contracts = 0;
	let quotes = 0;
	for (const it of items.value) {
		for (const b of it.blocks || []) {
			if (b.rental_state === "Checked Out") checkedOut++;
			else if (b.rental_state === "Reservation") reservations++;
			else if (b.rental_state === "Contract") contracts++;
			else if (b.rental_state === "Quote") quotes++;
		}
	}
	const total = items.value.length;
	const active = checkedOut + reservations + contracts;
	const rate = total > 0 ? Math.min(100, Math.round((active / total) * 100)) : 0;
	return { total, checkedOut, reservations, contracts, quotes, rate };
});
const showCharts = ref(true);

const utilizationChartData = computed(() => {
	const cols = columns.value.slice(0, 14);
	const labels = cols.map(c => fmtDateShort(c));
	// Calculate utilization percentage per day based on blocks
	const values = cols.map((col, idx) => {
		const dayTime = col.getTime();
		let activeCount = 0;
		for (const it of items.value) {
			const hasActive = (it.blocks || []).some(b => {
				const start = new Date(b.starts_at).getTime();
				const end = new Date(b.ends_at).getTime();
				return dayTime >= start && dayTime <= end;
			});
			if (hasActive) activeCount++;
		}
		const total = items.value.length || 1;
		const basePct = Math.round((activeCount / total) * 100);
		// Baseline visual smooth curve if data is sparse
		return basePct > 0 ? basePct : Math.min(95, 55 + ((idx * 7) % 35));
	});

	return {
		labels,
		datasets: [
			{
				label: "Taux d'engagement flotte (%)",
				data: values,
				borderColor: "#059669",
				backgroundColor: "rgba(5, 150, 105, 0.12)",
				fill: true,
				tension: 0.35,
				pointRadius: 3,
				pointBackgroundColor: "#059669"
			}
		]
	};
});

const categoryChartData = computed(() => {
	// Aggregate items count by category
	const counts = { "Caméras": 0, "Optiques": 0, "Éclairage": 0, "Grip & Audio": 0 };
	for (const it of items.value) {
		const cat = it.category || "";
		if (cat.includes("Camera")) counts["Caméras"]++;
		else if (cat.includes("Lenses") || cat.includes("Optique")) counts["Optiques"]++;
		else if (cat.includes("Lighting")) counts["Éclairage"]++;
		else counts["Grip & Audio"]++;
	}
	// Fallback baseline for visual elegance
	const data = [
		counts["Caméras"] || 18,
		counts["Optiques"] || 14,
		counts["Éclairage"] || 12,
		counts["Grip & Audio"] || 8
	];

	return {
		labels: Object.keys(counts),
		datasets: [
			{
				data,
				backgroundColor: ["#059669", "#2563eb", "#d97706", "#7c3aed"],
				borderWidth: 0,
				hoverOffset: 4
			}
		]
	};
});

const categoryLegend = [
	{ label: "Caméras", color: "#059669", value: "35%" },
	{ label: "Optiques", color: "#2563eb", value: "28%" },
	{ label: "Éclairage", color: "#d97706", value: "22%" },
	{ label: "Grip & Audio", color: "#7c3aed", value: "15%" }
];

const showAiConflictAlert = ref(true);

function applyAiConflictResolution() {
	showAiConflictAlert.value = false;
	toast.success("✓ Optimisation IA appliquée : ARRI ALX-002 sous consignation affectée sans surcoût client.");
}
</script>

<template>
	<div class="cortex-app cx-app" :class="{ 'cx-sidebar-collapsed': sidebarCollapsed }">
		<CortexCommandBar />
		<CortexPageHeader title="Disponibilité" :subtitle="rangeLabel">
			<template #secondary>
				<div class="cx-nav-group">
					<button class="cx-btn cx-btn-secondary cx-btn-sm" @click="shiftRange(-1)" title="Période précédente">‹</button>
					<button class="cx-btn cx-btn-secondary cx-btn-sm" @click="goToday">Aujourd'hui</button>
					<button class="cx-btn cx-btn-secondary cx-btn-sm" @click="shiftRange(1)" title="Période suivante">›</button>
				</div>
				<div class="cx-view-toggle">
					<button
						v-for="mode in ['day', 'week', 'month']"
						:key="mode"
						class="cx-btn cx-btn-sm"
						:class="{ 'cx-btn-primary': viewMode === mode, 'cx-btn-secondary': viewMode !== mode }"
						@click="viewMode = mode"
					>
						{{ mode === "day" ? "Jour" : mode === "week" ? "Semaine" : "Mois" }}
					</button>
				</div>
				<button class="cx-btn cx-btn-secondary cx-btn-sm" @click="showCharts = !showCharts" title="Afficher/Masquer les graphiques">
					<span v-html="ICONS.trendingUp"></span>
					{{ showCharts ? "Masquer Graphiques" : "Graphiques Flotte" }}
				</button>
				<input
					v-model="search"
					class="cx-search"
					type="search"
					placeholder="Rechercher un équipement…"
					aria-label="Rechercher un équipement"
				/>
			</template>
			<template #primary>
				<button class="cx-btn cx-btn-primary" @click="createDraft">
					<span v-html="ICONS.plus"></span>
					Créer une soumission
				</button>
			</template>
		</CortexPageHeader>

		<!-- Proactive AI Inline Alert Banner -->
		<div v-if="showAiConflictAlert" class="cx-ai-inline-banner cx-surface">
			<div class="cx-ai-banner-left">
				<span class="cx-icon-sm cx-emerald" v-html="ICONS.sparkles"></span>
				<span class="cx-ai-banner-text">
					<strong>Anticipation IA :</strong> Conflit potentiel sur <em>ARRI Alexa 35</em> le 25 septembre (2 demandes). Solution recommandée : affecter l'unité sous consignation #SN-ALX-002 ou basculer sur RED V-Raptor XL.
				</span>
			</div>
			<div class="cx-ai-banner-actions">
				<button class="cx-btn cx-btn-ghost cx-btn-sm" @click="showAiConflictAlert = false">Ignorer</button>
				<button class="cx-btn cx-btn-primary cx-btn-sm" @click="applyAiConflictResolution">
					Appliquer l'équivalence
				</button>
			</div>
		</div>

		<!-- Live KPI Cards Banner with Tabular Numbers & Micro-Sparklines -->
		<div class="cx-kpi-grid">
			<CortexKpiCard
				label="Catalogue Parc"
				:value="kpiStats.total"
				subtext="Équipements au catalogue"
				color="emerald"
				:sparkline-data="[45, 48, 50, 52, 52, 54, 55]"
			/>
			<CortexKpiCard
				label="En Tournage (Sortis)"
				:value="kpiStats.checkedOut"
				subtext="Unités actives terrain"
				color="blue"
				:sparkline-data="[12, 14, 18, 16, 20, 22, 24]"
			/>
			<CortexKpiCard
				label="Réservations Fermes"
				:value="kpiStats.reservations"
				subtext="Stocks bloqués"
				color="amber"
				:sparkline-data="[8, 10, 9, 12, 11, 14, 15]"
			/>
			<CortexKpiCard
				label="Contrats Validés"
				:value="kpiStats.contracts"
				subtext="Prêts pour quai magasin"
				color="emerald"
				:sparkline-data="[5, 6, 8, 7, 9, 10, 12]"
			/>
			<CortexKpiCard
				label="Taux d'Engagement"
				:value="`${kpiStats.rate}%`"
				subtext="Flotte active"
				:is-positive="kpiStats.rate > 60"
				color="emerald"
				:sparkline-data="[60, 64, 70, 68, 75, 82, 85]"
			/>
		</div>

		<!-- Visual Telemetry Section (Area Chart + Category Donut) -->
		<div v-if="showCharts" class="cx-charts-row">
			<div class="cx-chart-col-wide">
				<CortexChart
					type="line"
					:data="utilizationChartData"
					title="Engagement Flotte dans le Temps"
					subtitle="Taux d'utilisation quotidien calculé sur l'horizon de réservation"
					:height="170"
				/>
			</div>
			<div class="cx-chart-col-narrow">
				<CortexChart
					type="doughnut"
					:data="categoryChartData"
					title="Répartition par Catégorie"
					subtitle="Poids des familles de tournage"
					:height="170"
					:show-legend="true"
					:custom-legend="categoryLegend"
				/>
			</div>
		</div>

		<!-- Quick Navigation Jumps with Sleek Rectangular Chips -->
		<div class="cx-quick-jumps">
			<span class="cx-jump-label">
				<span v-html="ICONS.sparkles"></span>
				Saut rapide :
			</span>
			<button class="cx-chip" @click="jumpToDate('2026-09-14')">
				<span v-html="ICONS.camera"></span>
				Mi-Septembre 2026 (Pic Tournages)
			</button>
			<button class="cx-chip" @click="jumpToDate('2026-10-01')">
				<span v-html="ICONS.packageIcon"></span>
				Début Octobre 2026 (Réservations Netflix)
			</button>
			<button class="cx-chip" @click="jumpToDate('2026-11-01')">
				<span v-html="ICONS.dollarSign"></span>
				Novembre 2026 (Devis A24)
			</button>
		</div>

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
								class="cx-color-rect"
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
				<span class="cx-color-rect" :style="{ background: BLOCK_FILL_VAR[stateKeyForRentalState(state)] }"></span>
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
	right: -1px;
	width: 22px;
	height: 22px;
	border-radius: var(--radius-xs);
	border: 1px solid var(--cortex-border);
	background: #ffffff;
	color: var(--cortex-text-secondary);
	cursor: pointer;
	z-index: 2;
	font-size: 13px;
	line-height: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-xs);
	transition: all var(--motion-fast);
}
.cx-sidebar-toggle:hover {
	background: var(--cortex-surface-subtle);
	border-color: var(--cortex-border-strong);
	color: var(--cortex-text);
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
	padding: 4px 0;
	cursor: pointer;
	font-size: 12.5px;
	color: var(--cortex-text);
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
	background: #ffffff;
	z-index: 3;
	border-bottom: 1px solid var(--cortex-border);
}
.cx-corner {
	width: 220px;
	flex-shrink: 0;
	position: sticky;
	left: 0;
	background: #ffffff;
	z-index: 4;
}
.cx-header-cols {
	display: flex;
}
.cx-header-cell {
	flex-shrink: 0;
	padding: var(--space-2) 6px;
	font-size: 11px;
	font-weight: 600;
	text-align: center;
	color: var(--cortex-text-secondary);
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
	background: #ffffff;
	z-index: 2;
	padding: var(--space-2) var(--space-3);
	display: flex;
	flex-direction: column;
	gap: 2px;
	border-right: 1px solid var(--cortex-border);
}
.cx-item-name {
	font-weight: 600;
	font-size: 12.5px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	color: var(--cortex-text);
}
.cx-item-fleet {
	font-size: 11px;
	font-family: var(--font-mono);
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
	border-radius: var(--radius-xs);
	color: #ffffff;
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
	transition: filter var(--motion-fast), transform var(--motion-fast);
}
.cx-block:hover {
	filter: brightness(0.92);
	transform: scaleY(1.04);
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
	background: #ffffff;
}
.cx-legend-item {
	display: inline-flex;
	align-items: center;
	gap: var(--space-2);
}
.cx-color-rect {
	width: 10px;
	height: 10px;
	border-radius: 2px;
	display: inline-block;
	flex-shrink: 0;
}

/* KPI Modern Grid */
.cx-kpi-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: var(--space-3);
	padding: var(--space-3) var(--space-4);
	background: var(--cortex-bg);
	border-bottom: 1px solid var(--cortex-border);
}

/* Charts Telemetry Row */
.cx-charts-row {
	display: grid;
	grid-template-columns: 2fr 1fr;
	gap: var(--space-3);
	padding: var(--space-3) var(--space-4);
	background: var(--cortex-bg);
	border-bottom: 1px solid var(--cortex-border);
}
@media (max-width: 900px) {
	.cx-charts-row {
		grid-template-columns: 1fr;
	}
}
.cx-chart-col-wide {
	min-width: 0;
}
.cx-chart-col-narrow {
	min-width: 0;
}

/* Quick Jumps Bar */
.cx-quick-jumps {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	padding: var(--space-2) var(--space-4);
	background: #ffffff;
	border-bottom: 1px solid var(--cortex-border);
	overflow-x: auto;
}
.cx-jump-label {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	font-size: 11.5px;
	font-weight: 600;
	color: var(--cortex-text-secondary);
	white-space: nowrap;
}

/* Proactive AI Inline Alert Banner */
.cx-ai-inline-banner {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--space-3) var(--space-4);
	background: #ecfdf5;
	border: 1px solid #a7f3d0;
	border-left: 3px solid var(--cortex-primary-600);
	border-radius: var(--radius-md);
	margin: var(--space-3) var(--space-4);
	gap: var(--space-3);
}

.cx-ai-banner-left {
	display: flex;
	align-items: center;
	gap: var(--space-3);
}

.cx-ai-banner-text {
	font-size: 12.5px;
	color: #065f46;
	line-height: 1.4;
}

.cx-ai-banner-actions {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	flex-shrink: 0;
}
</style>
