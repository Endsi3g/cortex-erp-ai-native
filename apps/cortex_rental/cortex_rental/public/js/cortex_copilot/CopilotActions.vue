<script setup>
// Plusieurs boutons d'action consécutifs sous une réponse : une seule rangée discrète.
import CopilotProposalCard from "./CopilotProposalCard.vue";

defineProps({
	block: { type: Object, required: true }, // {blocks: [proposal…]}
});
const emit = defineEmits(["flow", "continue"]);
</script>

<template>
	<div class="cp-actions">
		<CopilotProposalCard v-for="(item, i) in block.blocks" :key="i" :block="item" @flow="(flow) => emit('flow', flow)" @continue="(t) => emit('continue', t)" />
	</div>
</template>

<style scoped>
.cp-actions {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
}
</style>
