<script setup>
defineProps({
	block: { type: Object, required: true }, // {fields, suggested_next_action}
});
</script>

<template>
	<div class="cp-missing">
		<p class="cp-missing-title">Il me manque :</p>
		<ul v-if="block.fields && block.fields.length">
			<li v-for="(f, i) in block.fields" :key="i">{{ f }}</li>
		</ul>
		<p v-if="block.suggested_next_action" class="cp-missing-next">{{ block.suggested_next_action }}</p>
	</div>
</template>

<style scoped>
.cp-missing {
	font-size: 14px;
	color: #1e293b;
}
.cp-missing-title {
	margin: 0 0 4px;
	font-weight: var(--cx-weight-strong, 600);
}
.cp-missing ul {
	margin: 0;
	padding-left: 18px;
}
.cp-missing-next {
	margin: 6px 0 0;
	font-size: 13px;
	color: #64748b;
}
</style>
