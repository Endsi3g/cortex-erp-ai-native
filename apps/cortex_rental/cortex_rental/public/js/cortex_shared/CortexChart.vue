<template>
	<div class="cx-chart-container" :style="{ minHeight: `${height}px` }">
		<div v-if="title || subtitle" class="cx-chart-header">
			<div v-if="title" class="cx-chart-title">{{ title }}</div>
			<div v-if="subtitle" class="cx-chart-subtitle">{{ subtitle }}</div>
		</div>

		<!-- Canvas for Chart.js -->
		<div class="cx-chart-canvas-wrap" :style="{ height: `${height}px` }">
			<canvas ref="canvasRef" class="cx-chart-canvas"></canvas>
			<!-- Fallback SVG when Chart.js is loading or unavailable -->
			<div v-if="!chartReady" class="cx-chart-fallback">
				<svg viewBox="0 0 400 160" preserveAspectRatio="none" class="cx-fallback-svg">
					<defs>
						<linearGradient id="fallbackGrad" x1="0" y1="0" x2="0" y2="1">
							<stop offset="0%" stop-color="#059669" stop-opacity="0.25" />
							<stop offset="100%" stop-color="#059669" stop-opacity="0.0" />
						</linearGradient>
					</defs>
					<path d="M 0 120 Q 80 50 160 80 T 320 40 T 400 30 L 400 160 L 0 160 Z" fill="url(#fallbackGrad)" />
					<path d="M 0 120 Q 80 50 160 80 T 320 40 T 400 30" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" />
				</svg>
			</div>
		</div>

		<!-- Optional Custom Legend -->
		<div v-if="showLegend && customLegend.length" class="cx-chart-legend">
			<div v-for="(item, idx) in customLegend" :key="idx" class="cx-legend-item">
				<span class="cx-legend-dot" :style="{ backgroundColor: item.color }"></span>
				<span class="cx-legend-label">{{ item.label }}</span>
				<span v-if="item.value !== undefined" class="cx-legend-val">{{ item.value }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";

const props = defineProps({
	type: { type: String, default: "line" }, // "line" | "bar" | "doughnut"
	data: { type: Object, required: true },
	options: { type: Object, default: () => ({}) },
	height: { type: Number, default: 180 },
	title: { type: String, default: "" },
	subtitle: { type: String, default: "" },
	showLegend: { type: Boolean, default: false },
	customLegend: { type: Array, default: () => [] }
});

const canvasRef = ref(null);
const chartReady = ref(false);
let chartInstance = null;

// Dynamic Chart.js singleton loader
let chartJsPromise = null;
function loadChartJs() {
	if (window.Chart) return Promise.resolve(window.Chart);
	if (chartJsPromise) return chartJsPromise;

	chartJsPromise = new Promise((resolve, reject) => {
		const script = document.createElement("script");
		script.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";
		script.async = true;
		script.onload = () => resolve(window.Chart);
		script.onerror = (err) => reject(err);
		document.head.appendChild(script);
	});
	return chartJsPromise;
}

async function renderChart() {
	if (!canvasRef.value) return;

	try {
		const Chart = await loadChartJs();
		if (!Chart) return;

		if (chartInstance) {
			chartInstance.destroy();
			chartInstance = null;
		}

		const ctx = canvasRef.value.getContext("2d");

		// Default sleek minimalist theme configuration
		const defaultScales = props.type === "doughnut" ? {} : {
			x: {
				grid: { display: false, drawBorder: false },
				ticks: {
					color: "#71717a",
					font: { family: "'Inter', sans-serif", size: 11 }
				}
			},
			y: {
				grid: { color: "#f4f4f5", drawBorder: false },
				ticks: {
					color: "#71717a",
					font: { family: "'JetBrains Mono', monospace", size: 11 },
					maxTicksLimit: 5
				}
			}
		};

		const defaultPlugins = {
			legend: { display: false },
			tooltip: {
				backgroundColor: "rgba(9, 9, 11, 0.9)",
				titleFont: { family: "'Inter', sans-serif", size: 12, weight: 600 },
				bodyFont: { family: "'JetBrains Mono', monospace", size: 12 },
				padding: 10,
				cornerRadius: 6,
				displayColors: true,
				boxPadding: 4
			}
		};

		chartInstance = new Chart(ctx, {
			type: props.type,
			data: props.data,
			options: {
				responsive: true,
				maintainAspectRatio: false,
				animation: { duration: 400, easing: "easeOutQuart" },
				scales: { ...defaultScales, ...(props.options.scales || {}) },
				plugins: { ...defaultPlugins, ...(props.options.plugins || {}) },
				...props.options
			}
		});

		chartReady.value = true;
	} catch (e) {
		console.warn("[CortexChart] Chart.js dynamic load fallback:", e);
	}
}

onMounted(() => {
	nextTick(() => {
		renderChart();
	});
});

watch(() => props.data, () => {
	renderChart();
}, { deep: true });

onBeforeUnmount(() => {
	if (chartInstance) {
		chartInstance.destroy();
		chartInstance = null;
	}
});
</script>

<style scoped>
.cx-chart-container {
	background: #ffffff;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-4);
	box-shadow: var(--shadow-xs);
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
}
.cx-chart-header {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.cx-chart-title {
	font-size: 13px;
	font-weight: 600;
	color: var(--cortex-text);
}
.cx-chart-subtitle {
	font-size: 11.5px;
	color: var(--cortex-text-muted);
}
.cx-chart-canvas-wrap {
	position: relative;
	width: 100%;
}
.cx-chart-canvas {
	width: 100% !important;
	height: 100% !important;
	display: block;
}
.cx-chart-fallback {
	position: absolute;
	inset: 0;
	display: flex;
	align-items: center;
	justify-content: center;
}
.cx-fallback-svg {
	width: 100%;
	height: 100%;
	opacity: 0.8;
}
.cx-chart-legend {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: var(--space-4);
	flex-wrap: wrap;
	padding-top: var(--space-2);
	border-top: 1px solid var(--cortex-border);
}
.cx-legend-item {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	font-size: 11.5px;
	color: var(--cortex-text-secondary);
}
.cx-legend-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
}
.cx-legend-label {
	font-weight: 500;
}
.cx-legend-val {
	font-family: var(--font-mono);
	font-weight: 600;
	color: var(--cortex-text);
}
</style>
