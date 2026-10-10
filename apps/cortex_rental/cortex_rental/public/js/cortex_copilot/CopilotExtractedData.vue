<script setup>
defineProps({
	block: { type: Object, required: true }, // {title, fields: [{label,value,confidence,evidence_id}]}
});

const CONFIDENCE_LABEL = { high: "confiance élevée", medium: "confiance moyenne", low: "confiance faible" };
</script>

<template>
	<section class="cp-extracted" :aria-label="block.title">
		<h3 class="cp-extracted-title">{{ block.title }}</h3>
		<dl>
			<template v-for="(field, i) in block.fields" :key="i">
				<dt>{{ field.label }}</dt>
				<dd>
					{{ field.value }}
					<span>({{ CONFIDENCE_LABEL[field.confidence] || field.confidence }})</span>
				</dd>
			</template>
		</dl>
	</section>
</template>

<style scoped>
.cp-extracted-title {
	margin: 0 0 6px;
	font-size: 14px;
	font-weight: var(--cx-weight-strong, 600);
	color: #0f172a;
}
dl {
	display: grid;
	grid-template-columns: max-content 1fr;
	gap: 4px 14px;
	margin: 0;
	font-size: 14px;
}
dt {
	color: #64748b;
}
dd {
	margin: 0;
	color: #1e293b;
}
dd span {
	font-size: 12px;
	color: #64748b;
}
</style>
