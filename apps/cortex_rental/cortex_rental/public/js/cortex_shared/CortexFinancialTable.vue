<script setup>
// Hierarchical financial statement table (design-system-accounting-
// pnl.md §13). Real `<table>`/`<th scope="col">` markup — not the
// flex-div grid CortexAvailability.vue uses for its calendar — because
// this is genuinely tabular data and §17 explicitly requires
// `th`/`scope="col"` for accessible financial tables.
import CortexAccountRow from "./CortexAccountRow.vue";

const props = defineProps({
	periods: { type: Array, required: true },
	accounts: { type: Array, required: true },
	currency: { type: String, default: "USD" },
	locale: { type: String, default: "en-US" },
	company: { type: String, default: "" },
	fiscalYear: { type: String, default: "" },
	fromDate: { type: String, default: "" },
	toDate: { type: String, default: "" },
});

const periodKeys = props.periods.map((p) => p.key);
</script>

<template>
	<div class="cx-financial-table-wrap cx-surface">
		<table class="cx-financial-table">
			<thead>
				<tr>
					<th scope="col" class="cx-financial-table-name-header">Account</th>
					<th v-for="p in periods" :key="p.key" scope="col" class="cx-financial-table-value-header">
						{{ p.label }}
					</th>
				</tr>
			</thead>
			<tbody>
				<CortexAccountRow
					v-for="node in accounts"
					:key="node.id"
					:node="node"
					:period-keys="periodKeys"
					:currency="currency"
					:locale="locale"
					:company="company"
					:fiscal-year="fiscalYear"
					:from-date="fromDate"
					:to-date="toDate"
				/>
			</tbody>
		</table>
	</div>
</template>

<style scoped>
.cx-financial-table-wrap {
	overflow-x: auto;
}
.cx-financial-table {
	width: 100%;
	border-collapse: collapse;
}
.cx-financial-table thead {
	background: var(--cortex-surface-subtle);
	position: sticky;
	top: 0;
}
.cx-financial-table th {
	height: 44px;
	padding: 0 var(--space-3);
	text-align: left;
	font-size: 12px;
	font-weight: 575;
	color: var(--cortex-text-secondary);
	white-space: nowrap;
}
.cx-financial-table-name-header {
	min-width: 320px;
}
.cx-financial-table-value-header {
	min-width: 160px;
	text-align: right !important;
}
</style>
