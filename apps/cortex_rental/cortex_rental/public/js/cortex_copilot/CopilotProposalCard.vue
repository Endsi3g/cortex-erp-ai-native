<script setup>
import { inject } from "vue";
// Proposition de l'assistant : elle ne crée rien. Le bouton ouvre le questionnaire « Nouvelle location » dans la conversation,
// où la personne choisit client, dates et équipement ; le prix vient du serveur et le devis n'est créé qu'à « Créer le devis ».
defineProps({
	block: { type: Object, required: true }, // {title, summary, impact, action, draft_id, requires_approval}
});
const emit = defineEmits(["flow", "continue"]);
// Dans l'accueil de l'assistant, le questionnaire s'ouvre dans la conversation ; ailleurs (panneau flottant), on ouvre la fiche.
const flowsEnabled = inject("cortexFlows", false);

function start() {
	if (flowsEnabled) emit("flow", { name: "quote" });
	else frappe.set_route("Form", "Cortex Rental Transaction", "new");
}
</script>

<template>
	<div class="cp-block cp-block-proposal">
		<div class="cp-block-head">
			<span class="cx-title-card">{{ block.title }}</span>
			<span v-if="block.requires_approval" class="cx-badge cp-approval-flag">approbation requise</span>
		</div>
		<p class="cx-text-body">{{ block.summary }}</p>
		<ul v-if="block.impact && block.impact.length" class="cp-impact-list">
			<li v-for="(line, i) in block.impact" :key="i" class="cx-text-meta">{{ line }}</li>
		</ul>
		<div class="cp-proposal-actions">
			<button type="button" class="cx-btn cx-btn-primary" @click="start">{{ flowsEnabled ? "Préparer le devis ici" : "Ouvrir le formulaire de devis" }}</button>
		</div>
	</div>
</template>

<style scoped>
.cp-block-proposal {
	background: #f6fbf8;
	border: 1px solid #d8eadf;
	border-radius: 12px;
	padding: 14px 16px;
}
.cp-block-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	margin-bottom: 6px;
}
.cx-title-card {
	font-size: 14px;
	font-weight: 600;
	color: #0f172a;
}
.cx-text-body {
	margin: 0 0 6px;
	font-size: 14px;
	color: #334155;
}
.cp-impact-list {
	margin: 0 0 10px;
	padding-left: 18px;
	color: #64748b;
	font-size: 12.5px;
}
.cp-approval-flag {
	padding: 2px 9px;
	border-radius: 999px;
	background: #fdf1de;
	color: #8a4b00;
	font-size: 11.5px;
	font-weight: 600;
}
.cp-proposal-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-top: 10px;
}
</style>
