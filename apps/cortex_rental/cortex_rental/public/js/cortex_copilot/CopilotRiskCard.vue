<script setup>
import { computed } from "vue";

const props = defineProps({
	block: { type: Object, required: true }, // {severity, title, explanation, source_ids}
});

const SEVERITY_META = {
	info: { label: "Info", tokenPrefix: "cortex-primary", glyph: "i" },
	warning: { label: "Attention", tokenPrefix: "cortex-warning", glyph: "!" },
	danger: { label: "Risque", tokenPrefix: "cortex-danger", glyph: "!" },
};

const meta = computed(() => SEVERITY_META[props.block.severity] || SEVERITY_META.warning);
</script>

<template>
	<div
		class="cp-block cp-block-risk"
		:style="{
			background: `var(--${meta.tokenPrefix}-50)`,
			borderColor: `var(--${meta.tokenPrefix}-100)`,
		}"
	>
		<div class="cp-block-head">
			<span class="cp-risk-glyph" :style="{ color: `var(--${meta.tokenPrefix}-600)` }" aria-hidden="true">{{
				meta.glyph
			}}</span>
			<span class="cx-title-card">{{ block.title }}</span>
			<span
				class="cx-badge"
				:style="{ background: `var(--${meta.tokenPrefix}-100)`, color: `var(--${meta.tokenPrefix}-700)` }"
				>{{ meta.label }}</span
			>
		</div>
		<p class="cx-text-body">{{ block.explanation }}</p>
		<div v-if="block.source_ids && block.source_ids.length" class="cp-source-chips">
			<span v-for="id in block.source_ids" :key="id" class="cx-text-mono cp-source-chip">{{ id }}</span>
		</div>
	</div>
</template>

<style scoped>
.cp-block-risk {
	border: 1px solid;
	border-radius: var(--radius-md);
	padding: var(--space-3);
}
.cp-block-head {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	margin-bottom: var(--space-2);
}
.cp-risk-glyph {
	font-weight: 700;
	width: 16px;
	text-align: center;
}
.cp-source-chips {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-1);
	margin-top: var(--space-2);
}
.cp-source-chip {
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-sm);
	padding: 1px 6px;
	font-size: 11px;
}
</style>
