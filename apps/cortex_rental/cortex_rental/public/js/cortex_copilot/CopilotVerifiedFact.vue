<script setup>
defineProps({
	block: { type: Object, required: true }, // {title, items, source_ids, checked_at}
});
</script>

<template>
	<div class="cp-block cp-block-fact">
		<div class="cp-block-head">
			<span class="cp-fact-icon" aria-hidden="true">✓</span>
			<span class="cx-title-card">{{ block.title }}</span>
		</div>
		<ul class="cp-fact-list">
			<li v-for="(item, i) in block.items" :key="i" class="cx-text-body">{{ item }}</li>
		</ul>
		<div v-if="block.source_ids && block.source_ids.length" class="cp-source-chips">
			<span v-for="id in block.source_ids" :key="id" class="cx-text-mono cp-source-chip">{{ id }}</span>
		</div>
		<p v-if="block.checked_at" class="cx-text-meta">Vérifié : {{ block.checked_at }}</p>
	</div>
</template>

<style scoped>
.cp-block-fact {
	background: var(--cortex-success-50);
	border: 1px solid var(--cortex-success-100);
	border-radius: var(--radius-md);
	padding: var(--space-3);
}
.cp-block-head {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	margin-bottom: var(--space-2);
}
.cp-fact-icon {
	color: var(--cortex-success-600);
	font-weight: 700;
}
.cp-fact-list {
	margin: 0 0 var(--space-2);
	padding-left: 18px;
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
