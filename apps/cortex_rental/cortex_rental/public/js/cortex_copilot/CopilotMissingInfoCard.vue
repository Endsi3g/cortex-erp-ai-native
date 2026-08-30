<script setup>
defineProps({
	block: { type: Object, required: true }, // {fields, suggested_next_action}
});
</script>

<template>
	<div class="cp-block cp-block-missing">
		<div class="cp-block-head">
			<span class="cp-missing-glyph" aria-hidden="true">?</span>
			<span class="cx-title-card">Information manquante</span>
		</div>
		<ul v-if="block.fields && block.fields.length" class="cp-missing-list">
			<li v-for="(f, i) in block.fields" :key="i" class="cx-text-body">{{ f }}</li>
		</ul>
		<p v-if="block.suggested_next_action" class="cx-text-meta">{{ block.suggested_next_action }}</p>
	</div>
</template>

<style scoped>
.cp-block-missing {
	background: var(--cortex-surface-subtle);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-3);
}
.cp-block-head {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	margin-bottom: var(--space-2);
}
.cp-missing-glyph {
	font-weight: 700;
	color: var(--cortex-text-secondary);
	width: 16px;
	text-align: center;
}
.cp-missing-list {
	margin: 0 0 var(--space-2);
	padding-left: 18px;
}
</style>
