<script setup>
defineProps({
	block: { type: Object, required: true }, // {title, fields: [{label,value,confidence,evidence_id}]}
});

const CONFIDENCE_LABEL = { high: "confiance élevée", medium: "confiance moyenne", low: "confiance faible" };
</script>

<template>
	<div class="cp-block cp-block-extracted">
		<div class="cp-block-head">
			<span class="cp-extracted-icon" aria-hidden="true">▤</span>
			<span class="cx-title-card">{{ block.title }}</span>
		</div>
		<dl class="cp-field-list">
			<template v-for="(field, i) in block.fields" :key="i">
				<dt class="cx-text-label">{{ field.label }}</dt>
				<dd class="cx-text-body">
					{{ field.value }}
					<span class="cx-text-meta">({{ CONFIDENCE_LABEL[field.confidence] || field.confidence }})</span>
				</dd>
			</template>
		</dl>
	</div>
</template>

<style scoped>
.cp-block-extracted {
	background: var(--cortex-violet-50);
	border: 1px solid var(--cortex-violet-100);
	border-radius: var(--radius-md);
	padding: var(--space-3);
}
.cp-block-head {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	margin-bottom: var(--space-2);
}
.cp-extracted-icon {
	color: var(--cortex-violet-600);
}
.cp-field-list {
	margin: 0;
	display: grid;
	grid-template-columns: max-content 1fr;
	gap: 4px var(--space-3);
}
.cp-field-list dd {
	margin: 0;
}
</style>
