<script setup>
// Accounting — Profit and Loss Statement (design-system-accounting-
// pnl.md). Real data via cortex_rental.api.v1.accounting.
// get_profit_and_loss, which wraps ERPNext's own P&L report.
//
// Company is shown read-only: get_company_context() resolves the tenant
// server-side from the caller's authorized Companies (PRD multi-tenant strict).
// Branch and Report View are disabled per spec (no backing filter in this report).
//
// Features added per drill-down:
// - Financial statements switcher dropdown (P&L active, BS/CF reserved).
// - Export menu (instant client-side CSV, Print/PDF @media print, ERPNext link).
// - Native datalists for Fiscal Year, Cost Center, and Finance Book autocomplete.
// - Filter context propagation for leaf account GL drill-down.
import { reactive, ref, computed, onMounted } from "vue";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexLoadingState from "../cortex_shared/CortexLoadingState.vue";
import CortexErrorState from "../cortex_shared/CortexErrorState.vue";
import CortexKpiSummary from "../cortex_shared/CortexKpiSummary.vue";
import CortexFinancialChart from "../cortex_shared/CortexFinancialChart.vue";
import CortexFinancialTable from "../cortex_shared/CortexFinancialTable.vue";
import CortexToast from "../cortex_shared/CortexToast.vue";
import { toast } from "../cortex_shared/toastBus.js";

const PERIODICITIES = ["Monthly", "Quarterly", "Half-Yearly", "Yearly"];

const filters = reactive({
	financeBook: "",
	fiscalYear: String(new Date().getFullYear()),
	fromDate: "",
	toDate: "",
	periodicity: "Monthly",
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

const displayCurrency = computed(() => filters.currency || "USD");
const companyLabel = computed(() => (report.value && report.value.company) || "—");
const hasData = computed(() => Boolean(report.value && report.value.accounts && report.value.accounts.length));

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

function exportToCsv() {
	exportMenuOpen.value = false;
	if (!report.value || !report.value.accounts) return;

	const periods = report.value.periods || [];
	const headers = ["Account", ...periods.map((p) => `"${p.label.replace(/"/g, '""')}"`)];
	const rows = [headers.join(",")];

	function appendNode(node) {
		const indent = "  ".repeat(node.depth || 0);
		const name = `"${(indent + node.name).replace(/"/g, '""')}"`;
		const vals = periods.map((p) => {
			const v = node.values && node.values[p.key] !== undefined ? node.values[p.key] : 0;
			return Number(v) || 0;
		});
		rows.push([name, ...vals].join(","));
		if (node.children && node.children.length) {
			node.children.forEach(appendNode);
		}
	}

	report.value.accounts.forEach(appendNode);

	// Summary KPI rows
	rows.push("");
	rows.push([`"Total Income"`, ...periods.map((p) => p.income || 0)].join(","));
	rows.push([`"Total Expense"`, ...periods.map((p) => p.expense || 0)].join(","));
	rows.push([`"Net Profit"`, ...periods.map((p) => p.profitLoss || 0)].join(","));

	const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent(rows.join("\n"));
	const link = document.createElement("a");
	link.setAttribute("href", csvContent);
	const periodLabel = filters.fiscalYear || `${filters.fromDate}_to_${filters.toDate}`;
	link.setAttribute("download", `Cortex_Pnl_${filters.periodicity}_${periodLabel}.csv`);
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	toast.success("✓ Export CSV généré et téléchargé avec succès !");
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

onMounted(() => {
	loadFilterOptions();
	fetchReport();
});
</script>

<template>
	<div class="cortex-app cx-app">
		<CortexToast />
		<CortexPageHeader title="Profit and Loss Statement" subtitle="Accounting">
			<template #secondary>
				<select class="cx-select-statement" aria-label="Sélectionner l'état financier">
					<option value="pnl" selected>Profit and Loss Statement</option>
					<option value="bs" disabled>Balance Sheet (Bientôt)</option>
					<option value="cf" disabled>Cash Flow Statement (Bientôt)</option>
				</select>

				<div class="cx-export-dropdown-wrap">
					<button
						type="button"
						class="cx-btn"
						:aria-expanded="exportMenuOpen"
						aria-label="Options d'exportation et actions"
						@click="toggleExportMenu"
					>
						<span>Actions / Export ▾</span>
					</button>
					<div v-if="exportMenuOpen" class="cx-export-dropdown-menu">
						<button type="button" class="cx-export-item" :disabled="!hasData" @click="exportToCsv">
							📥 Exporter en CSV
						</button>
						<button type="button" class="cx-export-item" :disabled="!hasData" @click="triggerPrint">
							🖨️ Imprimer / Sauvegarder PDF
						</button>
						<div class="cx-export-divider"></div>
						<button type="button" class="cx-export-item" @click="openStandardReport">
							↗ Ouvrir dans le rapport natif ERPNext
						</button>
					</div>
				</div>

				<button class="cx-btn" @click="fetchReport" aria-label="Actualiser le rapport">↻ Actualiser</button>
			</template>
		</CortexPageHeader>

		<section ref="toolbarEl" class="cx-toolbar cx-surface">
			<div class="cx-toolbar-grid">
				<div class="cx-field">
					<span class="cx-text-label">Company</span>
					<div class="cx-field-readonly">{{ companyLabel }}</div>
				</div>
				<div class="cx-field">
					<label class="cx-text-label" for="pnl-finance-book">Finance Book</label>
					<input
						id="pnl-finance-book"
						v-model="filters.financeBook"
						class="report-control"
						type="text"
						list="pnl-finance-books-list"
						placeholder="Principal"
					/>
					<datalist id="pnl-finance-books-list">
						<option v-for="fb in financeBooksList" :key="fb" :value="fb" />
					</datalist>
				</div>
				<div class="cx-field">
					<label class="cx-text-label" for="pnl-fiscal-year">Fiscal Year</label>
					<input
						id="pnl-fiscal-year"
						v-model="filters.fiscalYear"
						class="report-control"
						type="text"
						list="pnl-fiscal-years-list"
						:disabled="Boolean(filters.fromDate && filters.toDate)"
					/>
					<datalist id="pnl-fiscal-years-list">
						<option v-for="fy in fiscalYearsList" :key="fy" :value="fy" />
					</datalist>
				</div>
				<div class="cx-field">
					<label class="cx-text-label" for="pnl-from-date">From Date</label>
					<input id="pnl-from-date" v-model="filters.fromDate" class="report-control" type="date" />
				</div>
				<div class="cx-field">
					<label class="cx-text-label" for="pnl-to-date">To Date</label>
					<input id="pnl-to-date" v-model="filters.toDate" class="report-control" type="date" />
				</div>
				<div class="cx-field">
					<label class="cx-text-label" for="pnl-periodicity">Periodicity</label>
					<select id="pnl-periodicity" v-model="filters.periodicity" class="report-control">
						<option v-for="p in PERIODICITIES" :key="p" :value="p">{{ p }}</option>
					</select>
				</div>

				<div class="cx-field">
					<label class="cx-text-label" for="pnl-currency">Currency</label>
					<input id="pnl-currency" v-model="filters.currency" class="report-control" type="text" placeholder="USD" />
				</div>
				<div class="cx-field">
					<label class="cx-text-label" for="pnl-cost-center">Cost Center</label>
					<input
						id="pnl-cost-center"
						v-model="filters.costCenter"
						class="report-control"
						type="text"
						list="pnl-cost-centers-list"
					/>
					<datalist id="pnl-cost-centers-list">
						<option v-for="cc in costCentersList" :key="cc" :value="cc" />
					</datalist>
				</div>
				<div class="cx-field">
					<label class="cx-text-label cx-text-disabled" for="pnl-branch">Branch</label>
					<input
						id="pnl-branch"
						class="report-control"
						type="text"
						disabled
						placeholder="Non disponible"
						title="Aucun filtre Branch sur ce rapport"
					/>
				</div>
				<div class="cx-field">
					<label class="cx-text-label" for="pnl-project">Project</label>
					<input id="pnl-project" v-model="filters.project" class="report-control" type="text" />
				</div>
				<div class="cx-field">
					<label class="cx-text-label cx-text-disabled" for="pnl-report-view">Report View</label>
					<select id="pnl-report-view" class="report-control" disabled title="Une seule vue disponible pour l'instant">
						<option>Standard</option>
					</select>
				</div>
				<div class="cx-field cx-field-checkbox">
					<label class="cx-check">
						<input type="checkbox" v-model="filters.accumulatedValues" />
						<span>Accumulated Values</span>
					</label>
				</div>
			</div>

			<label class="cx-check cx-check-fb">
				<input type="checkbox" v-model="filters.includeDefaultBookEntries" />
				<span>Include Default FB Entries</span>
			</label>

			<div class="cx-toolbar-actions">
				<button class="cx-btn cx-btn-primary" @click="fetchReport">Appliquer</button>
			</div>
		</section>

		<div v-if="loading" style="padding: var(--space-4) 0">
			<CortexLoadingState :rows="6" :row-height="36" />
		</div>

		<div v-else-if="error" style="padding: var(--space-4) 0">
			<CortexErrorState :message="error" consequence="Aucun rapport n'a été chargé." @retry="fetchReport" />
		</div>

		<CortexEmptyState
			v-else-if="!hasData"
			message="No financial data available for the selected period."
			action-label="Adjust filters"
			@action="focusToolbar"
		/>

		<template v-else>
			<div class="cx-pnl-content-block" style="margin-top: var(--space-4)">
				<CortexKpiSummary
					:total-income="report.totalIncome"
					:total-expense="report.totalExpense"
					:net-profit="report.netProfit"
					:currency="displayCurrency"
				/>
			</div>
			<div class="cx-surface cx-pnl-content-block" style="margin-top: var(--space-4)">
				<CortexFinancialChart :periods="report.periods" :currency="displayCurrency" />
			</div>
			<div class="cx-pnl-content-block" style="margin-top: var(--space-4)">
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
</template>

<style scoped>
.cx-app {
	padding: 0 var(--space-6) var(--space-8);
}

.cx-select-statement {
	height: 36px;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	background: var(--cortex-surface);
	color: var(--cortex-text);
	padding: 0 var(--space-3);
	font-size: 13px;
	font-weight: 500;
	cursor: pointer;
}

.cx-export-dropdown-wrap {
	position: relative;
	display: inline-block;
}

.cx-export-dropdown-menu {
	position: absolute;
	top: 100%;
	right: 0;
	margin-top: 4px;
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	box-shadow: var(--shadow-popover, 0 8px 24px rgba(20, 27, 35, 0.12));
	min-width: 220px;
	padding: var(--space-1) 0;
	z-index: 50;
	display: flex;
	flex-direction: column;
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
	color: var(--cortex-text);
	cursor: pointer;
	transition: background var(--motion-fast);
}

.cx-export-item:hover:not(:disabled) {
	background: var(--cortex-surface-hover);
}

.cx-export-item:disabled {
	color: var(--cortex-text-disabled);
	cursor: not-allowed;
}

.cx-export-divider {
	height: 1px;
	background: var(--cortex-border);
	margin: var(--space-1) 0;
}

.cx-toolbar {
	padding: var(--space-4);
	margin-top: var(--space-2);
}
.cx-toolbar-grid {
	display: grid;
	grid-template-columns: repeat(6, 1fr);
	gap: var(--space-4);
}
.cx-field {
	display: flex;
	flex-direction: column;
	gap: var(--space-1);
}
.cx-field-readonly {
	height: 36px;
	display: flex;
	align-items: center;
	padding: 0 var(--space-3);
	border-radius: var(--radius-md);
	background: var(--cortex-surface-subtle);
	color: var(--cortex-text);
	font-size: 13px;
	font-weight: 500;
}
.cx-field-checkbox {
	justify-content: flex-end;
}
.cx-text-disabled {
	color: var(--cortex-text-disabled);
}

.report-control {
	height: 36px;
	border: 1px solid transparent;
	border-radius: var(--radius-md);
	background: var(--cortex-surface-subtle);
	color: var(--cortex-text-secondary);
	padding: 0 var(--space-3);
	font-size: 13px;
	font-family: inherit;
}
.report-control:not(:disabled):hover {
	background: var(--cortex-surface-hover);
}
.report-control:focus-visible {
	outline: none;
	border-color: var(--cortex-primary-500);
	box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}
.report-control:disabled {
	color: var(--cortex-text-disabled);
	cursor: not-allowed;
}

.cx-check {
	display: inline-flex;
	align-items: center;
	gap: var(--space-2);
	font-size: 14px;
	color: var(--cortex-text);
	cursor: pointer;
}
.cx-check-fb {
	margin-top: var(--space-4);
}

.cx-toolbar-actions {
	display: flex;
	justify-content: flex-end;
	margin-top: var(--space-4);
}

@media (max-width: 1279px) {
	.cx-toolbar-grid {
		grid-template-columns: repeat(3, 1fr);
	}
}
@media (max-width: 767px) {
	.cx-toolbar-grid {
		grid-template-columns: 1fr;
	}
	.cx-field-checkbox {
		justify-content: flex-start;
	}
}

@media print {
	.cx-toolbar,
	.cx-page-header-actions,
	.cx-select-statement,
	.cx-export-dropdown-wrap,
	.cx-btn {
		display: none !important;
	}
	.cx-app {
		padding: 0 !important;
	}
	.cx-pnl-content-block {
		page-break-inside: avoid;
	}
}
</style>
