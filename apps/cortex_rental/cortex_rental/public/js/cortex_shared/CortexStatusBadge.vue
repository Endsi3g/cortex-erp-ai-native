<script setup>
import { computed } from "vue";
import { STATE_META } from "./stateMeta.js";

const props = defineProps({
	state: { type: String, required: true }, // key into STATE_META
	label: { type: String, default: "" }, // override the default French label
	tooltip: { type: String, default: "" },
});

const meta = computed(() => STATE_META[props.state] || { label: props.state, glyph: "?", tokenPrefix: "state-draft" });
const displayLabel = computed(() => props.label || meta.value.label);
</script>

<template>
	<span
		class="cx-badge cx-status-badge"
		:style="{
			background: `var(--${meta.tokenPrefix}-bg)`,
			color: `var(--${meta.tokenPrefix}-text)`,
			borderColor: `var(--${meta.tokenPrefix}-border)`,
		}"
		:title="tooltip || displayLabel"
	>
		<span class="cx-status-glyph" aria-hidden="true">{{ meta.glyph }}</span>
		<span>{{ displayLabel }}</span>
	</span>
</template>

<style scoped>
.cx-status-glyph {
	font-weight: 700;
	line-height: 1;
}
</style>
