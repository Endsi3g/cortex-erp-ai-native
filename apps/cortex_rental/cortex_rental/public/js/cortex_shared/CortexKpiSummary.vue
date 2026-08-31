<script setup>
// KPI overview per design-system-accounting-pnl.md §11: Total Income
// − Total Expense = Net Profit, on one full-width card, amounts
// aligned on a shared baseline. Reused for any future financial
// statement screen (Balance Sheet, Cash Flow) that needs the same
// three-figure summary, not just P&L.
import { formatCurrency } from "./formatters.js";

defineProps({
	totalIncome: { type: Number, default: 0 },
	totalExpense: { type: Number, default: 0 },
	netProfit: { type: Number, default: 0 },
	currency: { type: String, default: "USD" },
	locale: { type: String, default: "en-US" },
});
</script>

<template>
	<div class="cx-kpi-summary cx-surface">
		<div class="cx-kpi-item">
			<span class="cx-text-label">Total Income</span>
			<span class="cx-text-kpi cx-tabular-nums">{{ formatCurrency(totalIncome, currency, locale) }}</span>
		</div>
		<span class="cx-kpi-operator" aria-hidden="true">−</span>
		<div class="cx-kpi-item">
			<span class="cx-text-label">Total Expense</span>
			<span class="cx-text-kpi cx-tabular-nums">{{ formatCurrency(totalExpense, currency, locale) }}</span>
		</div>
		<span class="cx-kpi-operator" aria-hidden="true">=</span>
		<div class="cx-kpi-item">
			<span class="cx-text-label">Net Profit</span>
			<span class="cx-text-kpi cx-kpi-profit cx-tabular-nums">{{ formatCurrency(netProfit, currency, locale) }}</span>
		</div>
	</div>
</template>

<style scoped>
.cx-kpi-summary {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: var(--space-6);
	padding: var(--space-6);
	flex-wrap: wrap;
}
.cx-kpi-item {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: var(--space-1);
	text-align: center;
	min-width: 160px;
}
.cx-kpi-operator {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 32px;
	height: 32px;
	border-radius: var(--radius-pill);
	background: var(--cortex-surface-subtle);
	color: var(--cortex-text-muted);
	font-size: 16px;
	font-weight: 600;
	flex-shrink: 0;
}
.cx-kpi-profit {
	color: var(--accounting-profit);
}

@media (max-width: 767px) {
	.cx-kpi-summary {
		flex-direction: column;
		gap: var(--space-4);
	}
	.cx-kpi-operator {
		transform: rotate(90deg);
	}
}
</style>
