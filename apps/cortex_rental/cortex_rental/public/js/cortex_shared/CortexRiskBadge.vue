<script setup>
import { computed } from "vue";
import { RISK_META } from "./stateMeta.js";

const props = defineProps({
	level: { type: String, required: true, validator: (v) => ["low", "medium", "high"].includes(v) },
	label: { type: String, default: "" },
});

const meta = computed(() => RISK_META[props.level]);
const displayLabel = computed(() => props.label || meta.value.label);
const glyph = computed(() => ({ low: "○", medium: "●", high: "!" })[props.level]);
</script>

<template>
	<span
		class="cx-badge cx-risk-badge"
		:style="{
			background: `var(--${meta.tokenPrefix}-bg)`,
			color: `var(--${meta.tokenPrefix}-text)`,
			borderColor: `var(--${meta.tokenPrefix}-border)`,
		}"
		:title="displayLabel"
	>
		<span aria-hidden="true" style="font-weight: 700">{{ glyph }}</span>
		<span>{{ displayLabel }}</span>
	</span>
</template>
