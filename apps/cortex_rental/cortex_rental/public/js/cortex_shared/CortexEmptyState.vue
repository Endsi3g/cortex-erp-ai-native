<script setup>
defineProps({
	message: { type: String, required: true },
	actionLabel: { type: String, default: "" },
});
defineEmits(["action"]);
</script>

<template>
	<div class="cx-empty-state">
		<slot name="icon" />
		<p class="cx-text-body" style="color: var(--cortex-text-muted); margin: var(--space-2) 0 0">
			{{ message }}
		</p>
		<button v-if="actionLabel" class="cx-btn" style="margin-top: var(--space-3)" @click="$emit('action')">
			{{ actionLabel }}
		</button>
	</div>
</template>

<style scoped>
.cx-empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	text-align: center;
	padding: var(--space-10) var(--space-6);
}
</style>
