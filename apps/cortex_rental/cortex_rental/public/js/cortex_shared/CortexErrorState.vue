<script setup>
// Rule from the spec: an error must state what did NOT happen (e.g.
// "no reservation was created") — never leave the consequence
// ambiguous. `consequence` is intentionally a required-by-convention
// prop (not enforced at runtime — this is plain Vue, no prop
// validators beyond type) rather than folded into `message` so callers
// can't skip it by accident.
defineProps({
	message: { type: String, required: true },
	consequence: { type: String, default: "" },
	retryLabel: { type: String, default: "Réessayer" },
});
defineEmits(["retry"]);
</script>

<template>
	<div class="cx-error-state" role="alert">
		<p class="cx-text-critical" style="margin: 0">{{ message }}</p>
		<p v-if="consequence" class="cx-text-meta" style="margin: var(--space-1) 0 0">{{ consequence }}</p>
		<button class="cx-btn" style="margin-top: var(--space-3)" @click="$emit('retry')">
			{{ retryLabel }}
		</button>
	</div>
</template>

<style scoped>
.cx-error-state {
	padding: var(--space-4);
	background: var(--cortex-danger-50);
	border: 1px solid var(--cortex-danger-100);
	border-radius: var(--radius-md);
}
</style>
