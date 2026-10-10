<script setup>
import { computed, reactive } from "vue";
import CopilotVerifiedFact from "./CopilotVerifiedFact.vue";
import CopilotExtractedData from "./CopilotExtractedData.vue";
import CopilotProposalCard from "./CopilotProposalCard.vue";
import CopilotActionCard from "./CopilotActionCard.vue";
import CopilotStatCard from "./CopilotStatCard.vue";
import CopilotRiskCard from "./CopilotRiskCard.vue";
import CopilotMissingInfoCard from "./CopilotMissingInfoCard.vue";
import CopilotApprovalCard from "./CopilotApprovalCard.vue";
import CopilotToolProgress from "./CopilotToolProgress.vue";
import CopilotErrorCard from "./CopilotErrorCard.vue";
import CopilotAssistantText from "./CopilotAssistantText.vue";
import CopilotActions from "./CopilotActions.vue";
import CopilotFlowQuote from "./CopilotFlowQuote.vue";
import CopilotFlowAvailability from "./CopilotFlowAvailability.vue";
import CopilotFlowApprovals from "./CopilotFlowApprovals.vue";
import CortexEmptyState from "../cortex_shared/CortexEmptyState.vue";

const props = defineProps({
	messages: { type: Array, required: true },
	sending: { type: Boolean, default: false },
	// Le panneau flottant fait défiler la conversation elle-même ; l'accueil de l'assistant la fait défiler dans son cadre.
	scroll: { type: Boolean, default: true },
});
const emit = defineEmits(["continue", "retry", "flow", "progress"]);

// Questionnaires guidés (accueil de l'assistant) : un message de l'assistant peut porter un `flow` au lieu de blocs.
const FLOWS = { quote: CopilotFlowQuote, availability: CopilotFlowAvailability, approvals: CopilotFlowApprovals };

// One place mapping the real backend block "type" discriminator (schemas/chat_schemas.py's ChatBlock union) to its renderer.
const BLOCK_COMPONENTS = {
	assistant_text: CopilotAssistantText,
	verified_fact: CopilotVerifiedFact,
	extracted_data: CopilotExtractedData,
	proposal: CopilotProposalCard,
	approval_required: CopilotApprovalCard,
	risk: CopilotRiskCard,
	missing_information: CopilotMissingInfoCard,
	tool_progress: CopilotToolProgress,
	error: CopilotErrorCard,
	proposal_group: CopilotActions,
	action_card: CopilotActionCard,
	stat_card: CopilotStatCard,
};

// Un type inconnu ne s'affiche jamais comme une erreur technique : s'il porte du texte, on le montre comme texte ;
// sinon on l'ignore (et on le note dans la console pour les développeurs).
function renderable(blocks) {
	const out = [];
	for (const block of blocks || []) {
		if (BLOCK_COMPONENTS[block.type]) out.push(block);
		else {
			if (typeof console !== "undefined") console.warn("Cortex : bloc de réponse ignoré", block && block.type);
			const text = block && (block.text || block.summary || block.message || block.safe_message);
			if (text) out.push({ type: "assistant_text", text: String(text) });
		}
	}
	// Boutons d'action consécutifs : une seule rangée.
	const merged = [];
	for (const block of out) {
		const last = merged[merged.length - 1];
		if (block.type === "proposal" && last && last.type === "proposal_group") last.blocks.push(block);
		else if (block.type === "proposal") merged.push({ type: "proposal_group", blocks: [block] });
		else merged.push(block);
	}
	return merged;
}

// Réponses fraîches : le texte apparaît d'abord, puis le reste (faits, boutons) se révèle.
const revealed = reactive({});
const needsReveal = (msg) => !!msg.fresh && (msg.blocks || []).some((b) => b.type === "assistant_text");
const isVisible = (msg, block) => !needsReveal(msg) || revealed[msg.id] || ["assistant_text", "tool_progress"].includes(block.type);

const hasMessages = computed(() => props.messages.length > 0);
</script>

<template>
	<div class="cp-conversation" :class="{ 'is-scroll': scroll }" role="log" aria-live="polite">
		<CortexEmptyState v-if="!hasMessages && !sending" message="Posez une question à Cortex pour commencer." />

		<div v-for="msg in messages" :key="msg.id" class="cp-message" :class="`cp-message-${msg.role}`">
			<template v-if="msg.role === 'user'">
				<p class="cp-user-bubble">{{ msg.text }}</p>
			</template>
			<component :is="FLOWS[msg.flow.name]" v-else-if="msg.flow" v-bind="msg.flow.props || {}" @quote="(props) => emit('flow', { name: 'quote', props })" />
			<template v-else>
				<template v-for="(block, i) in renderable(msg.blocks)" :key="i">
					<Transition name="cp-rise">
						<component
							:is="BLOCK_COMPONENTS[block.type]"
							v-if="isVisible(msg, block)"
							class="cp-block-item"
							:block="block"
							:animate="!!msg.fresh"
							@continue="(text) => emit('continue', text)"
							@retry="emit('retry', msg)"
							@flow="(flow) => emit('flow', flow)"
							@progress="emit('progress')"
							@revealed="revealed[msg.id] = true"
						/>
					</Transition>
				</template>
			</template>
		</div>

		<p v-if="sending" class="cp-pending" role="status"><span class="cp-shimmer">Cortex réfléchit…</span></p>
	</div>
</template>

<style scoped>
.cp-conversation {
	display: flex;
	flex-direction: column;
	gap: 22px;
	padding: var(--space-4, 16px);
}
.cp-conversation.is-scroll {
	flex: 1;
	overflow-y: auto;
}
.cp-message {
	min-width: 0;
}
.cp-message-user {
	display: flex;
	justify-content: flex-end;
}
.cp-user-bubble {
	max-width: 85%;
	margin: 0;
	padding: 9px 14px;
	border-radius: 18px;
	background: #f1f5f9;
	font-size: 15px;
	line-height: 1.5;
	color: #0f172a;
	white-space: pre-wrap;
}
.cp-message-assistant {
	display: flex;
	flex-direction: column;
	gap: 10px;
}
.cp-pending {
	margin: 0;
	font-size: 14.5px;
	color: #64748b;
}
.cp-shimmer {
	background: linear-gradient(90deg, #94a3b8 0%, #0f172a 45%, #94a3b8 90%);
	background-size: 220% 100%;
	-webkit-background-clip: text;
	background-clip: text;
	-webkit-text-fill-color: transparent;
	animation: cp-shimmer 1.3s linear infinite;
}
@keyframes cp-shimmer {
	from {
		background-position: 120% 0;
	}
	to {
		background-position: -100% 0;
	}
}
.cp-rise-enter-active {
	transition: opacity 0.28s ease, transform 0.28s ease;
}
.cp-rise-enter-from {
	opacity: 0;
	transform: translateY(6px);
}
@media (prefers-reduced-motion: reduce) {
	.cp-shimmer {
		animation: none;
		background: none;
		-webkit-text-fill-color: currentColor;
	}
	.cp-rise-enter-active {
		transition: none;
	}
}
</style>
