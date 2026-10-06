<script setup>
// Proposition de l'assistant : du texte et un bouton discret. Elle ne crée rien : le bouton ouvre un questionnaire
// où la personne choisit, le serveur calcule et rien n'est créé avant « Créer le devis ».
import { inject } from "vue";

const props = defineProps({
	block: { type: Object, required: true }, // {title, summary, impact, action, draft_id, requires_approval}
});
const emit = defineEmits(["flow", "continue"]);
// Dans l'accueil de l'assistant, le questionnaire s'ouvre dans la conversation ; ailleurs (panneau flottant), on ouvre la fiche.
const flowsEnabled = inject("cortexFlows", false);

const FLOW_OF = { open_quote_composer: "quote", create_quote_draft: "quote", open_availability_flow: "availability", open_approvals_flow: "approvals" };
const ROUTE_OF = {
	quote: ["Form", "Cortex Rental Transaction", "new"],
	availability: ["cortex-availability"],
	approvals: ["List", "Approval Request"],
};

function start() {
	const flow = FLOW_OF[props.block.action] || "quote";
	if (flowsEnabled) emit("flow", { name: flow });
	else frappe.set_route(ROUTE_OF[flow]);
}
</script>

<template>
	<div class="cp-proposal">
		<p v-if="block.summary" class="cp-proposal-summary">{{ block.summary }}</p>
		<ul v-if="block.impact && block.impact.length" class="cp-proposal-impact">
			<li v-for="(line, i) in block.impact" :key="i">{{ line }}</li>
		</ul>
		<button type="button" class="cp-ghost" @click="start">{{ block.title }}</button>
		<span v-if="block.requires_approval" class="cp-proposal-flag">approbation requise</span>
	</div>
</template>

<style scoped>
.cp-proposal {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 6px 10px;
}
.cp-proposal-summary,
.cp-proposal-impact {
	flex: 1 1 100%;
	margin: 0;
	font-size: 14px;
	color: #334155;
}
.cp-proposal-impact {
	padding-left: 18px;
	font-size: 12.5px;
	color: #64748b;
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
	transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.cp-ghost:hover {
	border-color: #cbd5e1;
	background: #f8fafc;
	color: #0f172a;
}
.cp-ghost:focus-visible {
	outline: 2px solid #047857;
	outline-offset: 2px;
}
.cp-proposal-flag {
	font-size: 12px;
	color: #8a4b00;
}
</style>
