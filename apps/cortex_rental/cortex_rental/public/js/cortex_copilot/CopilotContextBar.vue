<script setup>
defineProps({
	context: { type: Object, required: true }, // resolveDeskContext() shape
});

const PAGE_LABEL = {
	availability: "Disponibilité",
	transaction: "Transaction",
	dashboard: "Tableau de bord",
};
</script>

<template>
	<div class="cp-context-bar">
		<span class="cx-badge cp-context-chip">{{ PAGE_LABEL[context.page] || context.page }}</span>
		<span v-if="context.active_doctype" class="cx-badge cp-context-chip">
			{{ context.active_doctype }}<span v-if="context.active_document_name"> · {{ context.active_document_name }}</span>
		</span>
	</div>
</template>

<style scoped>
.cp-context-bar {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-2);
	padding: var(--space-2) var(--space-4);
	border-bottom: 1px solid var(--cortex-border);
	background: var(--cortex-surface-subtle);
}
.cp-context-chip {
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	color: var(--cortex-text-secondary);
}
</style>
