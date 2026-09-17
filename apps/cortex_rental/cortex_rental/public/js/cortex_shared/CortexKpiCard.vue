<template>
	<div class="cx-kpi-card">
		<div class="cx-kpi-top">
			<span class="cx-kpi-label">{{ label }}</span>
			<span v-if="badge" class="cx-badge cx-badge-success">{{ badge }}</span>
			<span v-else-if="icon" class="cx-kpi-icon-slot" v-html="icon"></span>
		</div>
		<div class="cx-kpi-main">
			<div class="cx-kpi-value">{{ value }}</div>
			<!-- Integrated SVG Micro-Sparkline -->
			<div v-if="sparklineData && sparklineData.length" class="cx-kpi-sparkline">
				<svg :viewBox="`0 0 ${sparkWidth} ${sparkHeight}`" preserveAspectRatio="none">
					<path :d="sparkAreaPath" :fill="sparkAreaFill" />
					<path :d="sparkLinePath" fill="none" :stroke="sparkStroke" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />
				</svg>
			</div>
		</div>
		<div v-if="subtext" class="cx-kpi-subtext" :class="{ 'cx-text-emerald': isPositive, 'cx-text-muted': !isPositive }">
			<span v-if="isPositive">↑</span>
			{{ subtext }}
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	label: { type: String, required: true },
	value: { type: [String, Number], required: true },
	subtext: { type: String, default: "" },
	badge: { type: String, default: "" },
	icon: { type: String, default: "" },
	isPositive: { type: Boolean, default: false },
	sparklineData: { type: Array, default: () => [30, 42, 38, 55, 62, 58, 72, 85] },
	color: { type: String, default: "emerald" }
});

const sparkWidth = 72;
const sparkHeight = 26;

const sparkStroke = computed(() => {
	if (props.color === "emerald") return "#059669";
	if (props.color === "blue") return "#2563eb";
	if (props.color === "amber") return "#d97706";
	return "#059669";
});

const sparkAreaFill = computed(() => {
	if (props.color === "emerald") return "rgba(5, 150, 105, 0.12)";
	if (props.color === "blue") return "rgba(37, 99, 235, 0.12)";
	if (props.color === "amber") return "rgba(217, 119, 6, 0.12)";
	return "rgba(5, 150, 105, 0.12)";
});

const sparkLinePath = computed(() => {
	const data = props.sparklineData;
	if (!data || data.length < 2) return "";
	const min = Math.min(...data);
	const max = Math.max(...data);
	const range = max - min || 1;
	const step = sparkWidth / (data.length - 1);

	return data.map((val, idx) => {
		const x = (idx * step).toFixed(1);
		const y = (sparkHeight - 2 - ((val - min) / range) * (sparkHeight - 6)).toFixed(1);
		return `${idx === 0 ? "M" : "L"} ${x} ${y}`;
	}).join(" ");
});

const sparkAreaPath = computed(() => {
	if (!sparkLinePath.value) return "";
	return `${sparkLinePath.value} L ${sparkWidth} ${sparkHeight} L 0 ${sparkHeight} Z`;
});
</script>

<style scoped>
.cx-kpi-card {
	background: #ffffff;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-3) var(--space-4);
	display: flex;
	flex-direction: column;
	gap: 6px;
	box-shadow: var(--shadow-xs);
	transition: transform var(--motion-fast), box-shadow var(--motion-fast);
}
.cx-kpi-card:hover {
	box-shadow: var(--shadow-sm);
	border-color: var(--cortex-border-strong);
	transform: translateY(-1px);
}
.cx-kpi-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.cx-kpi-label {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--cortex-text-secondary);
}
.cx-kpi-icon-slot {
	color: var(--cortex-text-muted);
	display: flex;
	align-items: center;
}
.cx-kpi-main {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 12px;
}
.cx-kpi-value {
	font-size: 24px;
	font-weight: 700;
	color: var(--cortex-text);
	font-variant-numeric: tabular-nums;
	line-height: 1.15;
}
.cx-kpi-sparkline {
	width: 72px;
	height: 26px;
	flex-shrink: 0;
}
.cx-kpi-sparkline svg {
	width: 100%;
	height: 100%;
	display: block;
}
.cx-kpi-subtext {
	font-size: 11.5px;
	font-weight: 500;
	display: flex;
	align-items: center;
	gap: 4px;
}
.cx-text-emerald {
	color: var(--cortex-emerald-600);
}
</style>
