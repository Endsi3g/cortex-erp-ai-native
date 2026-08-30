<script setup>
// Placeholder per the design-system scope: renders evidence chips with
// their metadata, but does not open a real secured preview/signed
// download — no such endpoint exists yet (Cortex Evidence Reference
// only stores a reference today, see services/evidence.py). Clicking
// emits "open" so a real page can wire actual behavior later without
// changing this component's contract.
defineProps({
	// items: [{ label, source?, date?, author?, hash?, confidence?: 'high'|'medium'|'low' }]
	items: { type: Array, required: true },
});
defineEmits(["open"]);
</script>

<template>
	<div class="cx-evidence-list">
		<button
			v-for="(item, i) in items"
			:key="i"
			class="cx-btn cx-evidence-chip"
			:title="[item.source, item.date, item.author].filter(Boolean).join(' · ')"
			@click="$emit('open', item)"
		>
			<span>{{ item.label }}</span>
			<span v-if="item.confidence" class="cx-text-meta cx-evidence-confidence">
				{{ { high: "confiance élevée", medium: "confiance moyenne", low: "confiance faible" }[item.confidence] }}
			</span>
			<span v-if="item.hash" class="cx-text-mono cx-evidence-hash">{{ item.hash.slice(0, 8) }}</span>
		</button>
	</div>
</template>

<style scoped>
.cx-evidence-list {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-2);
}
.cx-evidence-chip {
	font-size: 12.5px;
	padding: 4px var(--space-3);
}
.cx-evidence-confidence {
	margin-left: var(--space-2);
}
.cx-evidence-hash {
	margin-left: var(--space-2);
	color: var(--cortex-text-disabled);
}
</style>
