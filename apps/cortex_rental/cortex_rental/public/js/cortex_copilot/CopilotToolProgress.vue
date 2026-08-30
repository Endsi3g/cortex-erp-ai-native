<script setup>
import { computed } from "vue";

const props = defineProps({
	block: { type: Object, required: true }, // {tool_name, state, message}
});

const STATE_META = {
	running: { label: "En cours", glyph: "○" },
	success: { label: "Terminé", glyph: "✓" },
	failed: { label: "Échec", glyph: "✕" },
};
const meta = computed(() => STATE_META[props.block.state] || STATE_META.running);
</script>

<template>
	<div class="cp-tool-progress cx-text-meta">
		<span class="cx-text-mono">{{ block.tool_name }}</span>
		<span aria-hidden="true">{{ meta.glyph }}</span>
		<span>{{ meta.label }}</span>
		<span v-if="block.message">— {{ block.message }}</span>
	</div>
</template>

<style scoped>
.cp-tool-progress {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	padding: var(--space-1) 0;
}
</style>
