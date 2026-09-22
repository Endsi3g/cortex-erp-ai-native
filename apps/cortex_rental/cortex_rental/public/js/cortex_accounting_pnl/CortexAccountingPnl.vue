<script setup>
// Accounting — Profit and Loss Statement
// Visuellement aligné sur la référence hero_image.jpg :
//   • KPI strip plat 3 colonnes (Income − Expense = Profit) sans sparklines
//   • Graphique ligne unique (CortexFinancialChart) avec 3 séries
//   • Barre de filtres en grille 6 colonnes, fond page, sans carte élevée
//   • Tableau hiérarchique avec numéros de lignes
//   • Pas d'AI summary banner — données centrales, zéro décoration
//
// Données réelles via cortex_rental.api.v1.accounting.get_profit_and_loss
// (wrapping du rapport ERPNext standard).
// Company read-only : résolu server-side depuis les Companies autorisées
// de l'utilisateur (multi-tenant strict, PRD-ARCH).

import { reactive, ref, computed, onMounted } from "vue";
import CortexShell from "../cortex_shared/CortexShell.vue";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexLoadingState from "../cortex_shared/CortexLoadingState.vue";
import CortexErrorState from "../cortex_shared/CortexErrorState.vue";
import CortexEmptyState from "../cortex_shared/CortexEmptyState.vue";
import CortexFinancialChart from "../cortex_shared/CortexFinancialChart.vue";
import CortexFinancialTable from "../cortex_shared/CortexFinancialTable.vue";
import CortexToast from "../cortex_shared/CortexToast.vue";
import { toast } from "../cortex_shared/toastBus.js";
import { ICONS } from "../cortex_shared/CortexIcons.js";

const PERIODICITIES = ["Monthly", "Quarterly", "Half-Yearly", "Yearly"];

const filters = reactive({
	financeBook: "",
	fiscalYear: String(new Date().getFullYear()),
	fromDate: "",
	toDate: "",
	periodicity: "Quarterly",
	currency: "",
	costCenter: "",
	project: "",
	accumulatedValues: false,
	includeDefaultBookEntries: false,
});

const loading = ref(true);
const error = ref("");
const report = ref(null);
const toolbarEl = ref(null);
const exportMenuOpen = ref(false);

const fiscalYearsList = ref([]);
const costCentersList = ref([]);
const financeBooksList = ref([]);

const displayCurrency = computed(() => filters.currency || "CAD");
const companyLabel = computed(() => (report.value && report.value.company) || "—");
const hasData = computed(
	() => Boolean(report.value && report.value.accounts && report.value.accounts.length)
);

// KPI values straight from the API response
const totalIncome = computed(() => (report.value && report.value.totalIncome) || 0);
const totalExpense = computed(() => (report.value && report.value.totalExpense) || 0);
const netProfit = computed(() => (report.value && report.value.netProfit) || 0);
const marginPercentage = computed(() => {
	const income = totalIncome.value || 1;
	return Math.round((netProfit.value / income) * 100);
});

function fetchReport() {
	loading.value = true;
	error.value = "";
	exportMenuOpen.value = false;

	const args = {
		periodicity: filters.periodicity,
		accumulated_values: filters.accumulatedValues ? 1 : 0,
		include_default_book_entries: filters.includeDefaultBookEntries ? 1 : 0,
	};
	if (filters.fromDate && filters.toDate) {
		args.from_date = filters.fromDate;
		args.to_date = filters.toDate;
	} else {
		args.fiscal_year = filters.fiscalYear;
	}
	if (filters.costCenter) args.cost_center = filters.costCenter;
	if (filters.project) args.project = filters.project;
	if (filters.financeBook) args.finance_book = filters.financeBook;
	if (filters.currency) args.presentation_currency = filters.currency;

	if (typeof frappe === "undefined" || !frappe.call) {
		loading.value = false;
		error.value = "Environnement Frappe non disponible.";
		return;
	}

	frappe.call({
		method: "cortex_rental.api.v1.accounting.get_profit_and_loss",
		type: "GET",
		args,
		callback(r) {
			loading.value = false;
			report.value = (r.message && r.message.data) || null;
		},
		error(r) {
			loading.value = false;
			report.value = null;
			error.value =
				(r && r.responseJSON && (r.responseJSON.message || r.responseJSON.exc)) ||
				"Impossible de charger le rapport financier. Vérifiez la connexion au serveur.";
			toast.error(error.value);
		},
	});
}

function loadFilterOptions() {
	if (typeof frappe === "undefined" || !frappe.db || !frappe.db.get_list) return;
	frappe.db
		.get_list("Fiscal Year", { fields: ["name"], order_by: "year_start_date desc", limit: 20 })
		.then((res) => {
			if (res) fiscalYearsList.value = res.map((r) => r.name);
		})
		.catch(() => {});

	frappe.db
		.get_list("Cost Center", { fields: ["name"], limit: 50 })
		.then((res) => {
			if (res) costCentersList.value = res.map((r) => r.name);
		})
		.catch(() => {});

	frappe.db
		.get_list("Finance Book", { fields: ["name"], limit: 20 })
		.then((res) => {
			if (res) financeBooksList.value = res.map((r) => r.name);
		})
		.catch(() => {});
}

function focusToolbar() {
	if (toolbarEl.value) toolbarEl.value.scrollIntoView({ behavior: "smooth", block: "start" });
}

function toggleExportMenu() {
	exportMenuOpen.value = !exportMenuOpen.value;
}

function setPeriod(from, to) {
	filters.fromDate = from;
	filters.toDate = to;
	filters.fiscalYear = "";
	fetchReport();
}

function exportToCsv() {
	exportMenuOpen.value = false;
	if (!report.value || !report.value.accounts) return;

	const periods = report.value.periods || [];
	const headers = ["Account", ...periods.map((p) => `"${p.label.replace(/"/g, '""')}"`),];
	const rows = [headers.join(",")];

	function appendNode(node) {
		const indent = "  ".repeat(node.depth || 0);
		const name = `"${(indent + node.name).replace(/"/g, '""')}"`;
		const vals = periods.map((p) => {
			const v = node.values && node.values[p.key] !== undefined ? node.values[p.key] : 0;
			return Number(v) || 0;
		});
		rows.push([name, ...vals].join(","));
		if (node.children && node.children.length) node.children.forEach(appendNode);
	}

	report.value.accounts.forEach(appendNode);
	rows.push("");
	rows.push([`"Total Income"`, ...periods.map((p) => p.income || 0)].join(","));
	rows.push([`"Total Expense"`, ...periods.map((p) => p.expense || 0)].join(","));
	rows.push([`"Net Profit"`, ...periods.map((p) => p.profitLoss || 0)].join(","));

	const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent(rows.join("\n"));
	const link = document.createElement("a");
	link.setAttribute("href", csvContent);
	const periodLabel = filters.fiscalYear || `${filters.fromDate}_${filters.toDate}`;
	link.setAttribute("download", `Cortex_Pnl_${filters.periodicity}_${periodLabel}.csv`);
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	toast.success("✓ Export CSV généré avec succès !");
}

function triggerPrint() {
	exportMenuOpen.value = false;
	window.print();
}

function openStandardReport() {
	exportMenuOpen.value = false;
	if (typeof frappe !== "undefined" && frappe.set_route) {
		frappe.set_route("query-report", "Profit and Loss Statement");
	}
}

function formatCurrency(val) {
	if (val === undefined || val === null) return "$ 0.00";
	return new Intl.NumberFormat("en-CA", {
		style: "currency",
		currency: displayCurrency.value || "CAD",
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	}).format(val);
}

onMounted(() => {
	loadFilterOptions();
	fetchReport();
});
</script>

<template>
	<CortexShell active-page="pnl">
		<div class="cx-pnl-root">
			<CortexToast />

			<!-- ── Page Header ──────────────────────────────────────── -->
			<CortexPageHeader title="Profit and Loss Statement" subtitle="Accounting">
				<template #secondary>
					<!-- Financial statements switcher -->
					<select class="cx-select-statement" aria-label="Sélectionner l'état financier">
						<option value="pnl" selected>Financial Statements ◊</option>
						<option value="bs" disabled>Balance Sheet (Bientôt)</option>
						<option value="cf" disabled>Cash Flow (Bientôt)</option>
					</select>

					<!-- Export / Actions dropdown -->
					<div class="cx-export-wrap">
						<button
							type="button"
							class="cx-btn"
							:aria-expanded="exportMenuOpen"
							@click="toggleExportMenu"
						>
							Actions ◊
						</button>
						<div v-if="exportMenuOpen" class="cx-export-menu" role="menu">
							<button type="button" class="cx-export-item" role="menuitem" @click="exportToCsv">
								<span v-html="ICONS.fileText" class="cx-icon-sm" aria-hidden="true" />
								Exporter CSV
							</button>
							<button type="button" class="cx-export-item" role="menuitem" @click="triggerPrint">
								<span v-html="ICONS.printer" class="cx-icon-sm" aria-hidden="true" />
								Imprimer / PDF
							</button>
							<div class="cx-export-divider" role="separator" />
							<button
								type="button"
								class="cx-export-item"
								role="menuitem"
								@click="openStandardReport"
							>
								<span v-html="ICONS.arrowRight" class="cx-icon-sm" aria-hidden="true" />
								Ouvrir dans ERPNext
							</button>
						</div>
					</div>

					<!-- Refresh -->
					<button
						type="button"
						class="cx-btn cx-btn-icon"
						@click="fetchReport"
						aria-label="Actualiser le rapport"
					>
						<span v-html="ICONS.refresh" aria-hidden="true" />
					</button>

					<!-- More options (...) -->
					<button
						type="button"
						class="cx-btn cx-btn-icon"
						aria-label="Plus d'actions"
						@click="toggleExportMenu"
					>
						<span aria-hidden="true" style="font-weight: 700; letter-spacing: 1px; font-size: 14px;">···</span>
					</button>
				</template>
			</CortexPageHeader>

			<!-- ── Filter Bar ───────────────────────────────────────── -->
			<section ref="toolbarEl" class="cx-filter-bar">
				<!-- Row 1 -->
				<div class="cx-filter-grid">
					<!-- Company (read-only, server-resolved) -->
					<div class="cx-field">
						<div class="cx-field-readonly" :title="companyLabel">{{ companyLabel }}</div>
					</div>

					<!-- Finance Book -->
					<div class="cx-field">
						<input
							id="pnl-finance-book"
							v-model="filters.financeBook"
							class="cx-filter-input"
							type="text"
							list="pnl-finance-books-list"
							placeholder="Finance Book"
						/>
						<datalist id="pnl-finance-books-list">
							<option v-for="fb in financeBooksList" :key="fb" :value="fb" />
						</datalist>
					</div>

					<!-- Fiscal Year select -->
					<div class="cx-field">
						<select
							id="pnl-fiscal-year"
							v-model="filters.fiscalYear"
							class="cx-filter-input cx-select-with-arrow"
							:disabled="Boolean(filters.fromDate && filters.toDate)"
						>
							<option value="">Fiscal Year</option>
							<option v-for="fy in fiscalYearsList" :key="fy" :value="fy">{{ fy }}</option>
						</select>
					</div>

					<!-- From Date (2024-2025) -->
					<div class="cx-field">
						<input
							id="pnl-from-date"
							v-model="filters.fromDate"
							class="cx-filter-input"
							type="text"
							onfocus="(this.type='date')"
							onblur="if(!this.value)(this.type='text')"
							placeholder="2024-2025"
						/>
					</div>

					<!-- To Date (2024-2025) -->
					<div class="cx-field">
						<input
							id="pnl-to-date"
							v-model="filters.toDate"
							class="cx-filter-input"
							type="text"
							onfocus="(this.type='date')"
							onblur="if(!this.value)(this.type='text')"
							placeholder="2024-2025"
						/>
					</div>

					<!-- Periodicity -->
					<div class="cx-field">
						<select id="pnl-periodicity" v-model="filters.periodicity" class="cx-filter-input cx-select-with-arrow">
							<option v-for="p in PERIODICITIES" :key="p" :value="p">{{ p }}</option>
						</select>
					</div>
				</div>

				<!-- Row 2 -->
				<div class="cx-filter-grid" style="margin-top: 8px">
					<!-- Currency -->
					<div class="cx-field">
						<select id="pnl-currency" v-model="filters.currency" class="cx-filter-input cx-select-with-arrow">
							<option value="">Currency</option>
							<option value="CAD">CAD</option>
							<option value="USD">USD</option>
							<option value="EUR">EUR</option>
						</select>
					</div>

					<!-- Cost Center -->
					<div class="cx-field">
						<input
							id="pnl-cost-center"
							v-model="filters.costCenter"
							class="cx-filter-input"
							type="text"
							list="pnl-cost-centers-list"
							placeholder="Cost Center"
						/>
						<datalist id="pnl-cost-centers-list">
							<option v-for="cc in costCentersList" :key="cc" :value="cc" />
						</datalist>
					</div>

					<!-- Branch (disabled) -->
					<div class="cx-field">
						<input
							class="cx-filter-input"
							type="text"
							disabled
							placeholder="Branch"
							title="Aucun filtre Branch sur ce rapport"
						/>
					</div>

					<!-- Project -->
					<div class="cx-field">
						<input
							id="pnl-project"
							v-model="filters.project"
							class="cx-filter-input"
							type="text"
							placeholder="Project"
						/>
					</div>

					<!-- Report View -->
					<div class="cx-field">
						<select class="cx-filter-input cx-select-with-arrow" disabled title="Vue Standard uniquement">
							<option>Report View</option>
							<option selected>Standard</option>
						</select>
					</div>

					<!-- Accumulated Values checkbox -->
					<div class="cx-field cx-field-check-inline">
						<label class="cx-check-inline">
							<input type="checkbox" v-model="filters.accumulatedValues" />
							<span>Accumulated Values</span>
						</label>
					</div>
				</div>

				<!-- Row 3: FB entries + Apply -->
				<div class="cx-filter-footer">
					<label class="cx-check-inline">
						<input type="checkbox" v-model="filters.includeDefaultBookEntries" />
						<span>Include Default FB Entries</span>
					</label>
					<button type="button" class="cx-btn cx-btn-primary" @click="fetchReport">
						Appliquer
					</button>
				</div>
			</section>

			<!-- ── Loading ──────────────────────────────────────────── -->
			<div v-if="loading" class="cx-pnl-feedback">
				<CortexLoadingState :rows="6" :row-height="36" />
			</div>

			<!-- ── Error ────────────────────────────────────────────── -->
			<div v-else-if="error" class="cx-pnl-feedback">
				<CortexErrorState
					:message="error"
					consequence="Aucun rapport n'a été chargé."
					@retry="fetchReport"
				/>
			</div>

			<!-- ── Empty ────────────────────────────────────────────── -->
			<CortexEmptyState
				v-else-if="!hasData"
				message="Aucune donnée financière pour la période sélectionnée."
				action-label="Ajuster les filtres"
				@action="focusToolbar"
			/>

			<!-- ── Data ─────────────────────────────────────────────── -->
			<template v-else>
				<!-- KPI Strip — Image reference: flat 3-column, no sparklines -->
				<div class="cx-kpi-strip">
					<!-- Total Income -->
					<div class="cx-kpi-cell">
						<span class="cx-kpi-label">Total Income</span>
						<span class="cx-kpi-value cx-text-mono">{{ formatCurrency(totalIncome) }}</span>
					</div>

					<!-- Minus operator -->
					<div class="cx-kpi-op" aria-hidden="true">
						<span class="cx-kpi-op-symbol">−</span>
					</div>

					<!-- Total Expense -->
					<div class="cx-kpi-cell">
						<span class="cx-kpi-label">Total Expense</span>
						<span class="cx-kpi-value cx-text-mono">{{ formatCurrency(totalExpense) }}</span>
					</div>

					<!-- Equals operator -->
					<div class="cx-kpi-op" aria-hidden="true">
						<span class="cx-kpi-op-symbol">=</span>
					</div>

					<!-- Net Profit -->
					<div class="cx-kpi-cell">
						<span class="cx-kpi-label">Net Profit</span>
						<span
							class="cx-kpi-value cx-text-mono"
							:class="netProfit >= 0 ? 'cx-kpi-profit' : 'cx-kpi-loss'"
						>
							{{ formatCurrency(netProfit) }}
						</span>
					</div>
				</div>

				<!-- Line Chart — 3 series: Income / Expense / Net Profit -->
				<div class="cx-chart-panel">
					<CortexFinancialChart
						:periods="report.periods"
						:currency="displayCurrency"
						locale="en-CA"
					/>
				</div>

				<!-- Hierarchical P&L Table with row numbers -->
				<div class="cx-table-panel">
					<CortexFinancialTable
						:periods="report.periods"
						:accounts="report.accounts"
						:currency="displayCurrency"
						:company="report.company"
						:fiscal-year="filters.fiscalYear"
						:from-date="filters.fromDate"
						:to-date="filters.toDate"
					/>
				</div>
			</template>
		</div>
	</CortexShell>
</template>

<style scoped>
/* ── Root layout ──────────────────────────────────────── */
.cx-pnl-root {
	flex: 1;
	padding: var(--space-4) var(--space-6) var(--space-8);
	background: var(--cortex-canvas);
	min-width: 0;
}

/* ── Header actions ───────────────────────────────────── */
.cx-select-statement {
	height: 34px;
	padding: 0 var(--space-3);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	background: var(--cortex-surface);
	color: var(--cortex-text);
	font-size: 13px;
	font-weight: 500;
	cursor: pointer;
	font-family: inherit;
}

.cx-export-wrap {
	position: relative;
	display: inline-block;
}

.cx-export-menu {
	position: absolute;
	top: calc(100% + 4px);
	right: 0;
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	box-shadow: var(--shadow-lg);
	min-width: 220px;
	padding: var(--space-1) 0;
	z-index: 50;
}

.cx-export-item {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	width: 100%;
	padding: var(--space-2) var(--space-3);
	background: transparent;
	border: none;
	text-align: left;
	font-size: 13px;
	font-family: inherit;
	color: var(--cortex-text);
	cursor: pointer;
	transition: background var(--motion-fast);
}
.cx-export-item:hover { background: var(--cortex-surface-hover); }

.cx-export-divider {
	height: 1px;
	background: var(--cortex-border);
	margin: var(--space-1) 0;
}

/* Generic btn */
.cx-btn {
	height: 34px;
	padding: 0 var(--space-3);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	background: var(--cortex-surface);
	color: var(--cortex-text-secondary);
	font-size: 13px;
	font-family: inherit;
	cursor: pointer;
	transition: background var(--motion-fast);
	display: inline-flex;
	align-items: center;
	gap: var(--space-1);
}
.cx-btn:hover { background: var(--cortex-surface-hover); }

.cx-btn-icon {
	width: 34px;
	padding: 0;
	justify-content: center;
}

.cx-btn-primary {
	background: var(--cortex-emerald-600);
	border-color: var(--cortex-emerald-700);
	color: #fff;
	font-weight: 500;
}
.cx-btn-primary:hover { background: var(--cortex-emerald-700); }

.cx-icon-sm {
	display: inline-flex;
	align-items: center;
	width: 14px;
	height: 14px;
}

/* ── Filter bar ───────────────────────────────────────── */
/* Image ref: fields directly on page background, no card elevation */
.cx-filter-bar {
	background: transparent;
	border: none;
	padding: 0;
	margin-bottom: var(--space-6);
}

.cx-filter-grid {
	display: grid;
	grid-template-columns: repeat(6, 1fr);
	gap: 10px;
}

.cx-field {
	display: flex;
	flex-direction: column;
	position: relative;
}

.cx-filter-input,
.cx-field-readonly {
	height: 32px;
	border: 1px solid rgba(0, 0, 0, 0.08);
	border-radius: 8px;
	background: #f4f5f7;
	color: #1f2937;
	font-size: 13px;
	font-family: inherit;
	padding: 0 10px;
	width: 100%;
	transition: all 0.15s ease;
	appearance: none;
	-webkit-appearance: none;
}
.cx-filter-input::placeholder {
	color: #6b7280;
	font-size: 13px;
}
.cx-filter-input:focus-visible {
	outline: none;
	border-color: #9ca3af;
	background: #ffffff;
}
.cx-filter-input:disabled {
	color: #9ca3af;
	cursor: not-allowed;
	opacity: 0.7;
}

.cx-select-with-arrow {
	background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m7 15 5 5 5-5'/%3E%3Cpath d='m7 9 5-5 5 5'/%3E%3C/svg%3E");
	background-repeat: no-repeat;
	background-position: right 8px center;
	padding-right: 24px;
	cursor: pointer;
}

.cx-field-readonly {
	display: flex;
	align-items: center;
	font-weight: 500;
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis;
}

.cx-field-check-inline {
	display: flex;
	align-items: center;
	justify-content: flex-end;
}

.cx-check-inline {
	display: inline-flex;
	align-items: center;
	gap: var(--space-2);
	font-size: 13px;
	color: #374151;
	cursor: pointer;
}
.cx-check-inline input[type="checkbox"] {
	accent-color: #10b981;
	width: 14px;
	height: 14px;
}

.cx-filter-footer {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-top: 10px;
	padding-top: 10px;
}

/* ── Feedback (loading/error) ─────────────────────────── */
.cx-pnl-feedback {
	padding: var(--space-4) 0;
}

/* ── KPI Strip — Image ref: flat, 3 cols, operators ──── */
.cx-kpi-strip {
	display: flex;
	align-items: center;
	justify-content: center;
	background: transparent;
	border: none;
	margin: 20px 0 28px;
	gap: 48px;
}

.cx-kpi-cell {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	gap: 6px;
	border: none;
	padding: 0;
}

.cx-kpi-label {
	font-size: 13px;
	font-weight: 450;
	color: #6b7280;
	letter-spacing: 0.01em;
}

.cx-kpi-value {
	font-size: 24px;
	font-weight: 600;
	color: #111827;
	letter-spacing: -0.01em;
	line-height: 1.2;
}

.cx-kpi-profit {
	color: #22c55e;
}

.cx-kpi-loss {
	color: #ef4444;
}

/* Operator square — matches image: soft rounded rect */
.cx-kpi-op {
	flex-shrink: 0;
	display: flex;
	align-items: center;
	justify-content: center;
}

.cx-kpi-op-symbol {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 24px;
	height: 24px;
	border-radius: 6px;
	border: 1px solid #e5e7eb;
	font-size: 13px;
	font-weight: 600;
	color: #9ca3af;
	background: #ffffff;
	line-height: 1;
}

/* ── Chart panel ──────────────────────────────────────── */
.cx-chart-panel {
	background: #ffffff;
	border: none;
	padding: 12px 0 20px;
	margin-bottom: 20px;
}

/* ── Table panel ──────────────────────────────────────── */
.cx-table-panel {
	background: #ffffff;
	border-top: 1px solid #f3f4f6;
	border-radius: 0;
	overflow: hidden;
}

/* Mono text for numbers */
.cx-text-mono {
	font-family: var(--font-mono);
}

/* ── Responsive ───────────────────────────────────────── */
@media (max-width: 1279px) {
	.cx-filter-grid {
		grid-template-columns: repeat(3, 1fr);
	}
	.cx-kpi-value {
		font-size: 22px;
	}
}

@media (max-width: 767px) {
	.cx-filter-grid {
		grid-template-columns: repeat(2, 1fr);
	}
	.cx-kpi-strip {
		flex-direction: column;
	}
	.cx-kpi-cell {
		border-right: none;
		border-bottom: 1px solid var(--cortex-border);
		width: 100%;
	}
	.cx-kpi-op {
		transform: rotate(90deg);
		padding: var(--space-1) 0;
	}
	.cx-pnl-root {
		padding: var(--space-3) var(--space-3) var(--space-6);
	}
}

/* ── Print ────────────────────────────────────────────── */
@media print {
	.cx-filter-bar,
	.cx-btn,
	.cx-export-wrap,
	.cx-select-statement {
		display: none !important;
	}
	.cx-pnl-root {
		padding: 0 !important;
	}
}
</style>
