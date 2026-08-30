<script setup>
import CortexErrorState from "../cortex_shared/CortexErrorState.vue";

defineProps({
	block: { type: Object, required: true }, // {title, safe_message, retry_allowed}
});
const emit = defineEmits(["retry"]);
</script>

<template>
	<div class="cp-block cp-block-error">
		<p class="cx-title-card" style="margin: 0 0 var(--space-2)">{{ block.title }}</p>
		<CortexErrorState
			:message="block.safe_message"
			:retry-label="block.retry_allowed ? 'Réessayer' : 'Fermer'"
			@retry="emit('retry')"
		/>
	</div>
</template>
