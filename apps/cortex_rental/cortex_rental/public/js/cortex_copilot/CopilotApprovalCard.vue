<script setup>
import { computed } from "vue";
import CortexReadinessIndicator from "../cortex_shared/CortexReadinessIndicator.vue";

const props = defineProps({
	block: { type: Object, required: true }, // {approval_request_id, action_label, requirements, evidence_ids}
});

const readinessItems = computed(() =>
	(props.block.requirements || []).map((r, i) => ({ key: String(i), label: r.label, ready: r.passed })),
);

// Real navigation: the Approval Request Frappe Form exists today (core
// Desk form, not a custom page) — no fabricated "Approvals queue"
// screen to send this to instead.
function openApproval() {
	frappe.set_route("Form", "Approval Request", props.block.approval_request_id);
}
</script>

<template>
	<div class="cp-block cp-block-approval">
		<div class="cp-block-head">
			<span class="cx-title-card">Approbation humaine requise</span>
		</div>
		<p class="cx-text-body">{{ block.action_label }}</p>
		<CortexReadinessIndicator :items="readinessItems" />
		<button class="cx-btn cx-btn-primary" style="margin-top: var(--space-3)" @click="openApproval">
			Ouvrir la demande d'approbation
		</button>
	</div>
</template>

<style scoped>
.cp-block-approval {
	background: var(--cortex-warning-50);
	border: 1px solid var(--cortex-warning-100);
	border-radius: var(--radius-md);
	padding: var(--space-3);
}
.cp-block-head {
	margin-bottom: var(--space-2);
}
</style>
