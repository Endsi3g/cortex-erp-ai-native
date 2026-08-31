<script setup>
// Financial line chart (design-system-accounting-pnl.md §12): Income /
// Expense / Net Profit series. Hand-rolled inline SVG, not a charting
// library — this app has no npm/build step to vet a new dependency
// against (see cortex-tokens.css "Packaging"), and 3 lines over a
// handful of periods doesn't need one.
//
// Renders whatever accumulation state the backend already applied
// (the toolbar's "Accumulated Values" filter) rather than accumulating
// client-side again — avoids silently double-summing.
//
// Y-axis scale is computed from the real data's max value, not the
// spec mockup's fixed 0/250K/500K/750K/1M ticks — those only fit the
// sample dataset; hardcoding them would clip or misrepresent a report
// whose numbers are actually larger or smaller.
import { computed, ref } from "vue";
import { formatCurrency } from "./formatters.js";

const props = defineProps({
	periods: { type: Array, required: true },
	currency: { type: String, default: "USD" },
	locale: { type: String, default: "en-US" },
});

const SERIES = [
	{ key: "income", label: "Income", varName: "--accounting-income" },
	{ key: "expense", label: "Expense", varName: "--accounting-expense" },
	{ key: "profitLoss", label: "Net Profit/Loss", varName: "--accounting-profit" },
];

const WIDTH = 640;
const HEIGHT = 220;
const PAD = { top: 16, right: 16, bottom: 28, left: 48 };

const maxValue = computed(() => {
	const values = props.periods.flatMap((p) => SERIES.map((s) => Number(p[s.key]) || 0));
	return Math.max(0, ...values);
});

const axisMax = computed(() => {
	const max = maxValue.value || 1;
	const magnitude = Math.pow(10, Math.floor(Math.log10(max)));
	const step = magnitude / 2 || 1;
	return Math.ceil(max / step) * step || step;
});

const ticks = computed(() => {
	const n = 4;
	return Array.from({ length: n + 1 }, (_, i) => (axisMax.value / n) * i);
});

function fmtAxis(v) {
	if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(v % 1_000_000 ? 1 : 0)}M`;
	if (v >= 1_000) return `${(v / 1_000).toFixed(v % 1_000 ? 1 : 0)}K`;
	return String(Math.round(v));
}

function xFor(i) {
	const count = props.periods.length;
	if (count <= 1) return PAD.left + (WIDTH - PAD.left - PAD.right) / 2;
	return PAD.left + (i * (WIDTH - PAD.left - PAD.right)) / (count - 1);
}

function yFor(value) {
	const usable = HEIGHT - PAD.top - PAD.bottom;
	const ratio = axisMax.value ? value / axisMax.value : 0;
	return PAD.top + usable * (1 - ratio);
}

function pathFor(key) {
	return props.periods.map((p, i) => `${i === 0 ? "M" : "L"}${xFor(i)},${yFor(Number(p[key]) || 0)}`).join(" ");
}

function pointsFor(key) {
	return props.periods.map((p, i) => ({ x: xFor(i), y: yFor(Number(p[key]) || 0) }));
}

const hoverIndex = ref(-1);
const hoverSlotWidth = computed(() => (WIDTH - PAD.left - PAD.right) / Math.max(props.periods.length, 1));

// Percentage of the SVG's own coordinate space, not a pixel value — the
// SVG scales to 100% width via CSS, so a raw viewBox-unit pixel offset
// would drift from the visual point once the container isn't exactly
// WIDTH px wide.
const tooltipLeftPct = computed(() => (hoverIndex.value >= 0 ? (xFor(hoverIndex.value) / WIDTH) * 100 : 0));
</script>

<template>
	<div class="cx-financial-chart">
		<svg :viewBox="`0 0 ${WIDTH} ${HEIGHT}`" class="cx-chart-svg" role="img" aria-labelledby="cxChartTitle">
			<title id="cxChartTitle">Évolution du revenu, de la dépense et du profit net par période</title>

			<line
				v-for="(t, i) in ticks"
				:key="'grid-' + i"
				:x1="PAD.left"
				:x2="WIDTH - PAD.right"
				:y1="yFor(t)"
				:y2="yFor(t)"
				class="cx-chart-gridline"
			/>
			<text
				v-for="(t, i) in ticks"
				:key="'tick-' + i"
				:x="PAD.left - 8"
				:y="yFor(t) + 4"
				class="cx-chart-axis-label"
				text-anchor="end"
			>
				{{ fmtAxis(t) }}
			</text>
			<text
				v-for="(p, i) in periods"
				:key="'x-' + i"
				:x="xFor(i)"
				:y="HEIGHT - 6"
				class="cx-chart-axis-label"
				text-anchor="middle"
			>
				{{ p.label }}
			</text>

			<path
				v-for="s in SERIES"
				:key="s.key"
				:d="pathFor(s.key)"
				class="cx-chart-line"
				:style="{ stroke: `var(${s.varName})` }"
				fill="none"
			/>

			<g v-for="s in SERIES" :key="'pts-' + s.key">
				<circle
					v-for="(pt, i) in pointsFor(s.key)"
					:key="i"
					:cx="pt.x"
					:cy="pt.y"
					:r="hoverIndex === i ? 4 : 0"
					:style="{ fill: `var(${s.varName})` }"
					class="cx-chart-point"
				/>
			</g>

			<rect
				v-for="(p, i) in periods"
				:key="'hit-' + i"
				:x="xFor(i) - hoverSlotWidth / 2"
				y="0"
				:width="hoverSlotWidth"
				:height="HEIGHT - PAD.bottom"
				fill="transparent"
				@mouseenter="hoverIndex = i"
				@mouseleave="hoverIndex = -1"
			/>
		</svg>

		<div v-if="hoverIndex >= 0" class="cx-chart-tooltip" :style="{ left: tooltipLeftPct + '%' }">
			<p class="cx-text-label" style="margin: 0 0 var(--space-1)">{{ periods[hoverIndex].label }}</p>
			<p
				v-for="s in SERIES"
				:key="s.key"
				class="cx-text-meta"
				style="margin: 0; display: flex; align-items: center; gap: var(--space-2)"
			>
				<span class="cx-chart-legend-dot" :style="{ background: `var(${s.varName})` }"></span>
				{{ s.label }}: {{ formatCurrency(periods[hoverIndex][s.key], currency, locale) }}
			</p>
		</div>

		<div class="cx-chart-legend">
			<span v-for="s in SERIES" :key="s.key" class="cx-chart-legend-item">
				<span class="cx-chart-legend-dot" :style="{ background: `var(${s.varName})` }"></span>
				{{ s.label }}
			</span>
		</div>

		<table class="cx-sr-only">
			<caption>Données du graphique revenu / dépense / profit net</caption>
			<thead>
				<tr>
					<th scope="col">Période</th>
					<th v-for="s in SERIES" :key="s.key" scope="col">{{ s.label }}</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="p in periods" :key="p.key">
					<th scope="row">{{ p.label }}</th>
					<td v-for="s in SERIES" :key="s.key">{{ formatCurrency(p[s.key], currency, locale) }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<style scoped>
.cx-financial-chart {
	position: relative;
	padding: var(--space-8) var(--space-4) var(--space-4);
}
.cx-chart-svg {
	width: 100%;
	height: 280px;
	display: block;
}
.cx-chart-gridline {
	stroke: #f0f1f2;
	stroke-width: 1;
}
.cx-chart-axis-label {
	font-size: 10px;
	fill: var(--cortex-text-muted);
}
.cx-chart-line {
	stroke-width: 2;
}
.cx-chart-point {
	transition: r var(--motion-fast);
}
.cx-chart-tooltip {
	position: absolute;
	top: var(--space-2);
	transform: translateX(-50%);
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	box-shadow: var(--shadow-sm);
	padding: var(--space-2) var(--space-3);
	pointer-events: none;
	white-space: nowrap;
	z-index: 2;
}
.cx-chart-legend {
	display: flex;
	justify-content: center;
	gap: var(--space-5);
	padding-top: var(--space-2);
	font-size: 12px;
	color: var(--cortex-text-muted);
}
.cx-chart-legend-item {
	display: inline-flex;
	align-items: center;
	gap: var(--space-2);
}
.cx-chart-legend-dot {
	width: 12px;
	height: 12px;
	border-radius: 3px;
	display: inline-block;
	flex-shrink: 0;
}

@media (prefers-reduced-motion: reduce) {
	.cx-chart-point {
		transition: none;
	}
}
</style>
