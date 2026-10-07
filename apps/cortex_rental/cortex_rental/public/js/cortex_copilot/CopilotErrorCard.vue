<script setup>
defineProps({
	block: { type: Object, required: true }, // {title, safe_message, retry_allowed}
});
const emit = defineEmits(["retry"]);
</script>

<template>
	<div class="cp-error" role="alert">
		<p class="cp-error-text">
			<strong v-if="block.title">{{ block.title }}.</strong>
			{{ block.safe_message }}
		</p>
		<button v-if="block.retry_allowed" type="button" class="cp-ghost" @click="emit('retry')">Réessayer</button>
	</div>
</template>

<style scoped>
.cp-error {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 6px 12px;
}
.cp-error-text {
	flex: 1 1 auto;
	margin: 0;
	font-size: 14px;
	line-height: 1.5;
	color: #9b2c20;
}
.cp-ghost {
	height: 30px;
	padding: 0 12px;
	border: 1px solid #e2e8f0;
	border-radius: 999px;
	background: transparent;
	font: inherit;
	font-size: 13px;
	font-weight: 500;
	color: #334155;
	cursor: pointer;
}
.cp-ghost:hover {
	background: #f8fafc;
	border-color: #cbd5e1;
}
</style>
