<script setup>
import { ref, computed } from "vue";
import CortexReadinessIndicator from "../cortex_shared/CortexReadinessIndicator.vue";

const props = defineProps({
	block: { type: Object, required: true }, // {approval_request_id, action_label, requirements, evidence_ids}
});

const readinessItems = computed(() =>
	(props.block.requirements || []).map((r, i) => ({ key: String(i), label: r.label, ready: r.passed })),
);

const deciding = ref(false);
const resolvedStatus = ref(null); // 'approved' | 'rejected'
const showRejectInput = ref(false);
const rejectReason = ref("");
const errorMessage = ref("");

function openApproval() {
	if (props.block.approval_request_id) {
		frappe.set_route("Form", "Approval Request", props.block.approval_request_id);
	}
}

async function decide(decision) {
	deciding.value = true;
	errorMessage.value = "";
	try {
		if (decision === "reject" && (!rejectReason.value || rejectReason.value.trim().length < 3)) {
			throw new Error("Veuillez indiquer un motif de refus d'au moins 3 caractères.");
		}

		await new Promise((resolve, reject) => {
			frappe.call({
				method: "cortex_rental.api.v1.approval_queue.decide_approval",
				type: "POST",
				args: {
					name: props.block.approval_request_id,
					decision: decision,
					reason: decision === "reject" ? rejectReason.value : "Approuvé directement via le Copilote Cortex.",
				},
				callback: (r) => resolve(r.message || {}),
				error: (r) => reject(new Error(r.message || "Erreur lors de la prise de décision.")),
			});
		});

		resolvedStatus.value = decision === "approve" ? "approved" : "rejected";
		showRejectInput.value = false;
	} catch (err) {
		errorMessage.value = err.message || "Impossible d'enregistrer la décision.";
	} finally {
		deciding.value = false;
	}
}
</script>

<template>
	<div class="cp-block cp-block-approval">
		<div class="cp-block-head">
			<span class="cx-title-card">Approbation humaine requise</span>
			<span v-if="block.approval_request_id" class="cp-req-id">#{{ block.approval_request_id }}</span>
		</div>
		<p class="cx-text-body">{{ block.action_label }}</p>
		<CortexReadinessIndicator :items="readinessItems" />

		<!-- État Résolu : Approuvé ou Rejeté -->
		<div v-if="resolvedStatus === 'approved'" class="cp-resolved-status cp-status-approved">
			<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
				<polyline points="20 6 9 17 4 12"/>
			</svg>
			<span>Demande <strong>approuvée</strong> avec succès.</span>
		</div>

		<div v-else-if="resolvedStatus === 'rejected'" class="cp-resolved-status cp-status-rejected">
			<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
				<line x1="18" y1="6" x2="6" y2="18"/>
				<line x1="6" y1="6" x2="18" y2="18"/>
			</svg>
			<span>Demande <strong>refusée</strong>. Motif : {{ rejectReason }}</span>
		</div>

		<!-- État en attente : Boutons d'action directs -->
		<div v-else class="cp-approval-actions-wrap">
			<div class="cp-approval-btns">
				<button
					type="button"
					class="cx-btn cp-btn-approve"
					:disabled="deciding"
					@click="decide('approve')"
				>
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
						<polyline points="20 6 9 17 4 12"/>
					</svg>
					Approuver
				</button>
				<button
					type="button"
					class="cx-btn cp-btn-reject"
					:disabled="deciding"
					@click="showRejectInput = !showRejectInput"
				>
					Refuser…
				</button>
				<button
					type="button"
					class="cx-btn cp-btn-link"
					@click="openApproval"
				>
					Consulter ↗
				</button>
			</div>

			<!-- Zone de saisie du motif de refus -->
			<div v-if="showRejectInput" class="cp-reject-form">
				<input
					v-model="rejectReason"
					type="text"
					class="cp-reject-input"
					placeholder="Motif obligatoire du refus (min. 3 car.)"
					@keydown.enter.prevent="decide('reject')"
				/>
				<button
					type="button"
					class="cx-btn cp-btn-confirm-reject"
					:disabled="deciding || rejectReason.trim().length < 3"
					@click="decide('reject')"
				>
					Confirmer le refus
				</button>
			</div>
		</div>

		<p v-if="errorMessage" class="cp-approval-error">{{ errorMessage }}</p>
	</div>
</template>

<style scoped>
.cp-block-approval {
	background: var(--cortex-warning-50, #fffbeb);
	border: 1px solid var(--cortex-warning-100, #fef3c7);
	border-radius: var(--radius-md, 8px);
	padding: var(--space-3, 12px);
}

.cp-block-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: var(--space-2, 8px);
}

.cx-title-card {
	font-size: 13px;
	font-weight: 600;
	color: #0f172a;
}

.cp-req-id {
	font-size: 11px;
	color: #64748b;
	font-family: monospace;
}

.cx-text-body {
	font-size: 13px;
	line-height: 1.45;
	color: #334155;
	margin: 0 0 8px;
}

.cp-approval-actions-wrap {
	margin-top: 12px;
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.cp-approval-btns {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 8px;
}

.cp-btn-approve {
	background: #047857;
	color: #ffffff;
	border: none;
	border-radius: 6px;
	padding: 6px 12px;
	font-size: 12.5px;
	font-weight: 500;
	cursor: pointer;
	display: inline-flex;
	align-items: center;
	gap: 5px;
	transition: background 0.15s;
}

.cp-btn-approve:hover:not(:disabled) {
	background: #065f46;
}

.cp-btn-reject {
	background: #ffffff;
	color: #b91c1c;
	border: 1px solid #f87171;
	border-radius: 6px;
	padding: 6px 12px;
	font-size: 12.5px;
	font-weight: 500;
	cursor: pointer;
	transition: background 0.15s;
}

.cp-btn-reject:hover:not(:disabled) {
	background: #fef2f2;
}

.cp-btn-link {
	background: transparent;
	color: #64748b;
	border: none;
	font-size: 12px;
	cursor: pointer;
	padding: 6px 8px;
}

.cp-btn-link:hover {
	color: #0f172a;
}

.cp-reject-form {
	display: flex;
	gap: 6px;
	margin-top: 4px;
}

.cp-reject-input {
	flex: 1;
	height: 30px;
	padding: 0 8px;
	font-size: 12px;
	border: 1px solid #cbd5e1;
	border-radius: 6px;
	background: #ffffff;
}

.cp-btn-confirm-reject {
	background: #dc2626;
	color: #ffffff;
	border: none;
	border-radius: 6px;
	padding: 0 10px;
	font-size: 12px;
	cursor: pointer;
}

.cp-btn-confirm-reject:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.cp-resolved-status {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	border-radius: 6px;
	padding: 6px 10px;
	font-size: 12.5px;
	margin-top: 10px;
}

.cp-status-approved {
	background: #d1fae5;
	color: #065f46;
}

.cp-status-rejected {
	background: #fee2e2;
	color: #991b1b;
}

.cp-approval-error {
	margin: 8px 0 0;
	font-size: 12px;
	color: #dc2626;
}
</style>
