<script setup>
// Carte de statistiques de l'assistant : chiffres lus dans les données réelles de la société, avec en haut à droite une
// flèche qui ouvre l'endroit précis d'où ils viennent. Aucune valeur n'est estimée ici : on affiche ce que le serveur envoie.
import { computed } from "vue";
import { openDeskPath, isDeskPath } from "./chatClient.js";

const props = defineProps({
	block: { type: Object, required: true }, // {title, subtitle, kpis, series, source_label, source_href, checked_at}
});

const hasLink = computed(() => isDeskPath(props.block.source_href));
const series = computed(() => props.block.series);

// Mise en page du graphique : coordonnées calculées à partir des vraies valeurs (axe commençant à 0).
const W = 320;
const H = 120;
const PAD = { top: 18, right: 8, bottom: 22, left: 8 };
const plot = computed(() => {
	const s = series.value;
	if (!s || !s.values || !s.values.length) return null;
	const max = Math.max(...s.values, 0) || 1;
	const n = s.values.length;
	const innerW = W - PAD.left - PAD.right;
	const innerH = H - PAD.top - PAD.bottom;
	const step = innerW / n;
	const points = s.values.map((value, i) => ({
		x: PAD.left + step * i + step / 2,
		y: PAD.top + innerH - (value / max) * innerH,
		h: (value / max) * innerH,
		value,
		label: s.labels[i] || "",
	}));
	return { points, step, baseline: PAD.top + innerH, barWidth: Math.max(6, Math.min(28, step * 0.6)) };
});
const showValues = computed(() => (series.value ? series.value.values.length <= 7 : false));

function compact(value) {
	return new Intl.NumberFormat("fr-CA", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}
function full(value, unit) {
	const text = new Intl.NumberFormat("fr-CA", { maximumFractionDigits: 2 }).format(value);
	return unit ? `${text} ${unit}` : text;
}
const summary = computed(() => {
	const s = series.value;
	if (!s) return "";
	return `${props.block.title} : ` + s.values.map((v, i) => `${s.labels[i]} ${full(v, s.unit)}`).join(", ");
});
const linePath = computed(() => (plot.value ? plot.value.points.map((p, i) => `${i ? "L" : "M"}${p.x},${p.y}`).join(" ") : ""));

function checked(value) {
	const date = new Date(String(value || "").replace(" ", "T"));
	return Number.isNaN(date.getTime()) ? "" : date.toLocaleString("fr-CA", { dateStyle: "medium", timeStyle: "short" });
}
</script>

<template>
	<section class="cp-stat" :aria-label="block.title">
		<header class="cp-stat-head">
			<div class="cp-stat-titles">
				<h3 class="cp-stat-title">{{ block.title }}</h3>
				<p v-if="block.subtitle" class="cp-stat-sub">{{ block.subtitle }}</p>
			</div>
			<button
				v-if="hasLink"
				type="button"
				class="cp-stat-open"
				:aria-label="block.source_label || 'Ouvrir la source'"
				:title="block.source_label || 'Ouvrir la source'"
				@click="openDeskPath(block.source_href)"
			>
				<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M6 14 14 6M8 6h6v6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" /></svg>
			</button>
		</header>

		<ul v-if="block.kpis && block.kpis.length" class="cp-stat-kpis">
			<li v-for="(kpi, i) in block.kpis" :key="i" class="cp-stat-kpi" :class="`tone-${kpi.tone || 'neutral'}`">
				<span class="cp-stat-kpi-label">{{ kpi.label }}</span>
				<span class="cp-stat-kpi-value">{{ kpi.value }}</span>
				<span v-if="kpi.detail" class="cp-stat-kpi-detail">{{ kpi.detail }}</span>
			</li>
		</ul>

		<figure v-if="plot" class="cp-stat-chart">
			<svg :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="summary" preserveAspectRatio="xMidYMid meet">
				<line :x1="PAD.left" :x2="W - PAD.right" :y1="plot.baseline" :y2="plot.baseline" class="cp-axis" />
				<template v-if="series.kind === 'line'">
					<path :d="linePath" class="cp-line" fill="none" />
					<g v-for="(p, i) in plot.points" :key="i">
						<circle :cx="p.x" :cy="p.y" r="3" class="cp-dot"><title>{{ p.label }} : {{ full(p.value, series.unit) }}</title></circle>
						<text v-if="showValues" :x="p.x" :y="p.y - 7" class="cp-value" text-anchor="middle">{{ compact(p.value) }}</text>
					</g>
				</template>
				<template v-else>
					<g v-for="(p, i) in plot.points" :key="i">
						<rect :x="p.x - plot.barWidth / 2" :y="plot.baseline - Math.max(p.h, p.value ? 1 : 0)" :width="plot.barWidth" :height="Math.max(p.h, p.value ? 1 : 0)" rx="3" class="cp-bar">
							<title>{{ p.label }} : {{ full(p.value, series.unit) }}</title>
						</rect>
						<text v-if="showValues" :x="p.x" :y="plot.baseline - p.h - 5" class="cp-value" text-anchor="middle">{{ compact(p.value) }}</text>
					</g>
				</template>
				<text v-for="(p, i) in plot.points" :key="`l${i}`" :x="p.x" :y="H - 6" class="cp-label" text-anchor="middle">{{ p.label }}</text>
			</svg>
			<figcaption v-if="series.unit" class="cp-stat-unit">Unité : {{ series.unit }}</figcaption>
		</figure>

		<p v-if="block.checked_at" class="cp-stat-meta">Données vérifiées le {{ checked(block.checked_at) }}</p>
	</section>
</template>

<style scoped>
.cp-stat {
	border: 1px solid #e2e8f0;
	border-radius: 10px;
	background: #ffffff;
	padding: 12px;
}
.cp-stat-head {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 8px;
}
.cp-stat-titles {
	min-width: 0;
}
.cp-stat-title {
	margin: 0;
	font-size: 14px;
	font-weight: 650;
	color: #0f172a;
}
.cp-stat-sub {
	margin: 2px 0 0;
	font-size: 12.5px;
	color: #64748b;
}
.cp-stat-open {
	flex: none;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 28px;
	height: 28px;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	background: transparent;
	color: #475569;
	cursor: pointer;
	transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.cp-stat-open:hover {
	border-color: #cbd5e1;
	background: #f8fafc;
	color: #0f172a;
}
.cp-stat-open:focus-visible {
	outline: 2px solid #047857;
	outline-offset: 2px;
}
.cp-stat-kpis {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
	gap: 8px;
	margin: 10px 0 0;
	padding: 0;
	list-style: none;
}
.cp-stat-kpi {
	display: flex;
	flex-direction: column;
	gap: 1px;
	padding: 8px 10px;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	background: #f8fafc;
}
.cp-stat-kpi-label {
	font-size: 12px;
	color: #64748b;
}
.cp-stat-kpi-value {
	font-size: 18px;
	font-weight: 650;
	font-variant-numeric: tabular-nums;
	color: #0f172a;
}
.cp-stat-kpi-detail {
	font-size: 12px;
	color: #64748b;
}
.tone-good .cp-stat-kpi-value {
	color: #065f46;
}
.tone-warn .cp-stat-kpi-value {
	color: #8a4b00;
}
.tone-bad .cp-stat-kpi-value {
	color: #b42318;
}
.cp-stat-chart {
	margin: 12px 0 0;
}
.cp-stat-chart svg {
	display: block;
	width: 100%;
	height: auto;
	max-height: 170px;
}
.cp-axis {
	stroke: #cbd5e1;
	stroke-width: 1;
}
.cp-bar {
	fill: #047857;
}
.cp-line {
	stroke: #047857;
	stroke-width: 2;
}
.cp-dot {
	fill: #047857;
}
.cp-value {
	font-size: 10px;
	fill: #334155;
}
.cp-label {
	font-size: 10px;
	fill: #64748b;
}
.cp-stat-unit {
	margin-top: 2px;
	font-size: 12px;
	color: #64748b;
}
.cp-stat-meta {
	margin: 8px 0 0;
	font-size: 12px;
	color: #64748b;
}
@media (prefers-reduced-motion: reduce) {
	.cp-stat-open {
		transition: none;
	}
}
</style>
