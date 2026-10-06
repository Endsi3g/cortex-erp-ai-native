<script setup>
import { computed } from "vue";
import CopilotVerifiedFact from "./CopilotVerifiedFact.vue";
import CopilotExtractedData from "./CopilotExtractedData.vue";
import CopilotProposalCard from "./CopilotProposalCard.vue";
import CopilotRiskCard from "./CopilotRiskCard.vue";
import CopilotMissingInfoCard from "./CopilotMissingInfoCard.vue";
import CopilotApprovalCard from "./CopilotApprovalCard.vue";
import CopilotToolProgress from "./CopilotToolProgress.vue";
import CopilotErrorCard from "./CopilotErrorCard.vue";
import CopilotAssistantText from "./CopilotAssistantText.vue";
import CopilotFlowQuote from "./CopilotFlowQuote.vue";
import CopilotFlowAvailability from "./CopilotFlowAvailability.vue";
import CopilotFlowApprovals from "./CopilotFlowApprovals.vue";
import CortexLoadingState from "../cortex_shared/CortexLoadingState.vue";
import CortexEmptyState from "../cortex_shared/CortexEmptyState.vue";

const props = defineProps({
	messages: { type: Array, required: true },
	sending: { type: Boolean, default: false },
});
const emit = defineEmits(["continue", "retry", "flow"]);

// Questionnaires guidés (accueil de l'assistant) : un message de l'assistant peut porter un `flow` au lieu de blocs.
const FLOWS = { quote: CopilotFlowQuote, availability: CopilotFlowAvailability, approvals: CopilotFlowApprovals };

// One place mapping the real backend block "type" discriminator
// (schemas/chat_schemas.py's ChatBlock union) to its renderer — add a
// case here the day a 9th block type is added server-side, nowhere else.
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
};

function componentFor(block) {
	return BLOCK_COMPONENTS[block.type] || CopilotErrorCard;
}

function fallbackBlock(block) {
	// An unrecognized type (future block added server-side, this
	// frontend not yet updated) renders as a visible error rather than
	// silently vanishing.
	if (BLOCK_COMPONENTS[block.type]) return block;
	return { title: "Type de contenu non reconnu", safe_message: `type: ${block.type}`, retry_allowed: false };
}

const hasMessages = computed(() => props.messages.length > 0);
</script>

<template>
	<div class="cp-conversation" role="log" aria-live="polite">
		<CortexEmptyState v-if="!hasMessages && !sending" message="Posez une question à Cortex pour commencer." />

		<div v-for="msg in messages" :key="msg.id" class="cp-message" :class="`cp-message-${msg.role}`">
			<template v-if="msg.role === 'user'">
				<p class="cx-text-body cp-user-bubble">{{ msg.text }}</p>
			</template>
			<component :is="FLOWS[msg.flow.name]" v-else-if="msg.flow" v-bind="msg.flow.props || {}" @quote="(props) => emit('flow', { name: 'quote', props })" />
			<template v-else>
				<component
					:is="componentFor(block)"
					v-for="(block, i) in msg.blocks"
					:key="i"
					:block="fallbackBlock(block)"
					@continue="(text) => emit('continue', text)"
					@retry="emit('retry', msg)"
					@flow="(flow) => emit('flow', flow)"
				/>
			</template>
		</div>

		<div v-if="sending" class="cp-sending">
			<CortexLoadingState :rows="2" :row-height="40" />
		</div>
	</div>
</template>

<style scoped>
.cp-conversation {
	flex: 1;
	overflow-y: auto;
	padding: var(--space-4);
	display: flex;
	flex-direction: column;
	gap: var(--space-4);
}
.cp-message-user {
	display: flex;
	justify-content: flex-end;
}
.cp-user-bubble {
	background: var(--cortex-primary-600);
	color: var(--cortex-inverse);
	border-radius: var(--radius-lg);
	padding: var(--space-2) var(--space-3);
	max-width: 85%;
	margin: 0;
}
.cp-message-assistant {
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
}
</style>
