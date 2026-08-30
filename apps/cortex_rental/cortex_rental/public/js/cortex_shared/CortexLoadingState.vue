<script setup>
// Rule from the spec: loading must render a skeleton, never a fake
// "available"/zero value — callers must not render real-looking
// numbers while a request is in flight.
defineProps({
	rows: { type: Number, default: 4 },
	rowHeight: { type: Number, default: 32 },
});
</script>

<template>
	<div class="cx-loading-state" role="status" aria-live="polite" aria-label="Chargement en cours">
		<div
			v-for="n in rows"
			:key="n"
			class="cx-skeleton"
			:style="{ height: rowHeight + 'px', marginBottom: 'var(--space-2)' }"
		></div>
	</div>
</template>
