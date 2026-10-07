<script setup>
defineProps({
	block: { type: Object, required: true }, // {severity, title, explanation, source_ids}
});
</script>

<template>
	<p class="cp-note" :class="`is-${block.severity || 'warning'}`" role="note">
		<strong>{{ block.title }}.</strong>
		{{ block.explanation }}
	</p>
</template>

<style scoped>
.cp-note {
	margin: 0;
	padding-left: 12px;
	border-left: 2px solid #f3c77a;
	font-size: 13px;
	line-height: 1.5;
	color: #6b4300;
}
.cp-note.is-danger {
	border-left-color: #e8a29b;
	color: #8f1d12;
}
.cp-note.is-info {
	border-left-color: #cbd5e1;
	color: #475569;
}
</style>
