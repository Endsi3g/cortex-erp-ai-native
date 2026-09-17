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
	availability: [
		{ label: "Vérifier la disponibilité", message: "Vérifie la disponibilité des caméras pour la semaine prochaine." },
		{ label: "Caméras ARRI en tournage", message: "Quelles caméras ARRI sont actuellement en tournage ?" },
		{ label: "Créer un devis Dune 3", message: "Prépare un brouillon de devis pour Dune 3 Productions." },
	],
	transaction: [
		{ label: "Résumer le dossier", message: "Résume cette transaction et ses lignes d'équipements." },
		{ label: "Vérifier solvabilité & assurance", message: "Vérifie la préparation : compte client, assurance, paiement." },
		{ label: "Vérifier la règle 7j=3j", message: "Vérifie l'application de la règle tarifaire 7j=3j." },
	],
	checkin: [
		{ label: "Retours en retard (Overdue)", message: "Y a-t-il des retours en retard sur les locations en cours ?" },
		{ label: "Articles en quarantaine", message: "Quels équipements sont actuellement en quarantaine pour diagnostic ?" },
	],
	dashboard: [
		{ label: "Priorités du jour", message: "Résume mes priorités de location et sorties aujourd'hui." },
		{ label: "Retours prévus cette semaine", message: "Quels sont les retours prévus cette semaine ?" },
		{ label: "Disponibilité Alexa 35", message: "Quelle est la disponibilité de l'ARRI Alexa 35 ce mois-ci ?" },
	],
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
