<script setup>
// One row of a hierarchical financial statement (design-system-
// accounting-pnl.md §13 "Arbre de comptes"). Recursive Vue 3 SFC — a
// component can invoke itself by its own filename inside its template
// without an explicit import/registration (documented Vue 3 SFC
// behavior). Root is a `<tr>`, plus a sibling `<template v-if>` holding
// child rows: Vue 3 multi-root ("fragment") components are required for
// this to stay valid `<table>` markup all the way down.
//
// Drill-down: clicking leaf accounts (type === "account") navigates
// directly to ERPNext's General Ledger report filtered for this account,
// company, and period.
import { ref } from "vue";
import { formatCurrency } from "./formatters.js";

const props = defineProps({
	node: { type: Object, required: true },
	periodKeys: { type: Array, required: true },
	currency: { type: String, default: "USD" },
	locale: { type: String, default: "en-US" },
	company: { type: String, default: "" },
	fiscalYear: { type: String, default: "" },
	fromDate: { type: String, default: "" },
	toDate: { type: String, default: "" },
});

const expanded = ref(true);
const hasChildren = Boolean(props.node.children && props.node.children.length);

function toggle() {
	expanded.value = !expanded.value;
}

function displayValue(v) {
	return formatCurrency(Number(v) || 0, props.currency, props.locale);
}

function openGeneralLedger() {
	if (props.node.type === "group") return;
	if (typeof frappe !== "undefined" && frappe.set_route) {
		const routeOptions = {
			company: props.company,
			account: props.node.id || props.node.name,
		};
		if (props.fromDate && props.toDate) {
			routeOptions.from_date = props.fromDate;
			routeOptions.to_date = props.toDate;
		} else if (props.fiscalYear) {
			routeOptions.fiscal_year = props.fiscalYear;
		}
		frappe.route_options = routeOptions;
		frappe.set_route("query-report", "General Ledger");
	}
}
</script>

<template>
	<tr class="cx-account-row" :class="{ 'cx-account-row-group': node.type === 'group' }">
		<td class="cx-account-row-name-cell">
			<span class="cx-account-row-indent" :style="{ width: node.depth * 24 + 'px' }" aria-hidden="true"></span>
			<button
				v-if="hasChildren"
				type="button"
				class="cx-account-row-toggle"
				:aria-expanded="expanded"
				:aria-label="(expanded ? 'Réduire ' : 'Développer ') + node.name"
				@click="toggle"
			>
				<span class="cx-chevron" :class="{ 'cx-chevron-expanded': expanded }" aria-hidden="true">›</span>
			</button>
			<span v-else class="cx-account-row-toggle-spacer" aria-hidden="true"></span>
			
			<button
				v-if="node.type === 'account'"
				type="button"
				class="cx-account-link-btn"
				title="Ouvrir dans le Grand Livre (General Ledger)"
				@click="openGeneralLedger"
			>
				<span class="cx-account-row-name">{{ node.name }}</span>
				<span class="cx-account-drilldown-icon" aria-hidden="true">↗</span>
			</button>
			<span v-else class="cx-account-row-name">{{ node.name }}</span>
		</td>
		<td
			v-for="key in periodKeys"
			:key="key"
			class="cx-account-row-value cx-tabular-nums"
			:class="{
				'cx-value-negative': Number(node.values[key]) < 0,
				'cx-value-zero': !Number(node.values[key]),
			}"
		>
			{{ displayValue(node.values[key]) }}
		</td>
	</tr>
	<template v-if="hasChildren && expanded">
		<CortexAccountRow
			v-for="child in node.children"
			:key="child.id"
			:node="child"
			:period-keys="periodKeys"
			:currency="currency"
			:locale="locale"
			:company="company"
			:fiscal-year="fiscalYear"
			:from-date="fromDate"
			:to-date="toDate"
		/>
	</template>
</template>

<style scoped>
.cx-account-row td {
	padding: var(--space-2) var(--space-3);
	border-bottom: 1px solid var(--cortex-surface-subtle);
	font-size: 13.5px;
	font-weight: 450;
}
.cx-account-row:hover td {
	background: var(--cortex-surface-hover);
}
.cx-account-row-group td {
	font-weight: 600;
}
.cx-account-row-name-cell {
	display: flex;
	align-items: center;
	gap: var(--space-1);
	min-width: 320px;
}
.cx-account-row-indent {
	flex-shrink: 0;
}
.cx-account-row-toggle,
.cx-account-row-toggle-spacer {
	width: 28px;
	height: 28px;
	flex-shrink: 0;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border: none;
	background: transparent;
	color: var(--cortex-text-muted);
	cursor: pointer;
	border-radius: var(--radius-sm);
	padding: 0;
}
.cx-chevron {
	display: inline-block;
	transition: transform var(--motion-fast);
}
.cx-chevron-expanded {
	transform: rotate(90deg);
}
.cx-account-row-name {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cx-account-link-btn {
	display: inline-flex;
	align-items: center;
	gap: var(--space-1);
	background: transparent;
	border: none;
	padding: 2px 6px;
	margin: -2px -6px;
	border-radius: var(--radius-sm);
	color: var(--cortex-text);
	font-size: inherit;
	font-family: inherit;
	font-weight: inherit;
	cursor: pointer;
	text-align: left;
	transition: background var(--motion-fast), color var(--motion-fast);
}
.cx-account-link-btn:hover {
	background: var(--color-brand-50, #eef7ff);
	color: var(--color-brand-600, #0d72c7);
}
.cx-account-drilldown-icon {
	font-size: 11px;
	opacity: 0;
	color: var(--color-brand-500, #1683dc);
	transition: opacity var(--motion-fast);
}
.cx-account-link-btn:hover .cx-account-drilldown-icon {
	opacity: 1;
}
.cx-account-row-value {
	min-width: 160px;
	text-align: right;
	font-variant-numeric: tabular-nums;
}
.cx-value-zero {
	color: var(--cortex-text-disabled);
	font-weight: 400 !important;
}
.cx-value-negative {
	color: var(--cortex-danger-600);
}
</style>
