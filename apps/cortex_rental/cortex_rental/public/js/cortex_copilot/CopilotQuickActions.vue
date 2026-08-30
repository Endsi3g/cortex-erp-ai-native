<script setup>
import { computed } from "vue";

const props = defineProps({
	page: { type: String, required: true },
	disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["run"]);

// Only pages this frontend can actually resolve today (see
// chatClient.js's resolveDeskContext) get real quick actions — no
// button here pretends a Check-in/Consignment/Approvals page exists
// yet (see HANDOFF.md for those screens' status).
const ACTIONS_BY_PAGE = {
	availability: [{ label: "Vérifier la disponibilité", message: "Vérifie la disponibilité pour ce que je regarde." }],
	transaction: [
		{ label: "Résumer", message: "Résume cette transaction." },
		{ label: "Vérifier la préparation", message: "Vérifie la préparation : compte, assurance, paiement." },
	],
	dashboard: [{ label: "Résumer mes priorités", message: "Résume mes priorités aujourd'hui." }],
};

const actions = computed(() => ACTIONS_BY_PAGE[props.page] || ACTIONS_BY_PAGE.dashboard);
</script>

<template>
	<div v-if="actions.length" class="cp-quick-actions">
		<button
			v-for="action in actions"
			:key="action.label"
			class="cx-btn"
			:disabled="disabled"
			@click="emit('run', action.message)"
		>
			{{ action.label }}
		</button>
	</div>
</template>

<style scoped>
.cp-quick-actions {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-2);
	padding: var(--space-2) var(--space-4);
	border-bottom: 1px solid var(--cortex-border);
}
</style>
