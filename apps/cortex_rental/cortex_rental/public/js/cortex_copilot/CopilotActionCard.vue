<script setup>
// Carte dédiée d'une action proposée par l'assistant : aperçu (lignes et totaux), puis Approuver / Refuser.
// Rien n'est fait avant l'approbation; l'état (fait, refusé, périmé, échec) vient toujours du serveur.
import { computed, ref } from "vue";
import { decideAction, openDeskPath, isDeskPath } from "./chatClient.js";

const props = defineProps({
	block: { type: Object, required: true }, // {action_id, title, subtitle, rows, totals, status, approve_label, message, result_label, result_href}
});

const status = ref(props.block.status || "Proposed");
const message = ref(props.block.message || "");
const resultLabel = ref(props.block.result_label || "");
const resultHref = ref(props.block.result_href || "");
const deciding = ref(false);

const open = computed(() => status.value === "Proposed");
const hasLink = computed(() => resultLabel.value && isDeskPath(resultHref.value));
const BADGE = {
	Proposed: ["À approuver", "is-pending"],
	Executed: ["Fait", "is-done"],
	Rejected: ["Refusée", "is-muted"],
	Failed: ["Échec", "is-bad"],
	Expired: ["Périmée", "is-muted"],
};
const badge = computed(() => BADGE[status.value] || BADGE.Proposed);

async function decide(approve) {
	if (deciding.value || !open.value) return;
	deciding.value = true;
	message.value = "";
	try {
		const out = await decideAction(props.block.action_id, approve);
		status.value = out.status || (approve ? "Executed" : "Rejected");
		message.value = out.ok && status.value === "Executed" ? "" : out.message || "";
		resultLabel.value = out.result_label || "";
		resultHref.value = out.result_href || "";
	} catch (err) {
		// Une erreur de réseau ou de droits : la carte reste à approuver, rien n'est présenté comme fait.
		message.value = err.message || "Impossible d'enregistrer la décision. Réessayez.";
	} finally {
		deciding.value = false;
	}
}
</script>

<template>
	<section class="cp-action" :class="`is-${status.toLowerCase()}`" :aria-label="block.title">
		<header class="cp-action-head">
			<h3 class="cp-action-title">{{ block.title }}</h3>
			<span class="cp-action-badge" :class="badge[1]">{{ badge[0] }}</span>
		</header>
		<p v-if="block.subtitle" class="cp-action-sub">{{ block.subtitle }}</p>

		<table v-if="block.rows && block.rows.length" class="cp-action-table">
			<tbody>
				<tr v-for="(row, i) in block.rows" :key="`r${i}`">
					<td class="cp-action-label">
						{{ row.label }}
						<span v-if="row.detail" class="cp-action-detail">{{ row.detail }}</span>
					</td>
					<td v-if="row.value" class="cp-action-value">{{ row.value }}</td>
				</tr>
				<tr v-for="(row, i) in block.totals" :key="`t${i}`" class="cp-action-total" :class="{ 'is-last': i === block.totals.length - 1 }">
					<td class="cp-action-label">{{ row.label }}</td>
					<td class="cp-action-value">{{ row.value }}</td>
				</tr>
			</tbody>
		</table>

		<footer class="cp-action-foot">
			<template v-if="open">
				<button type="button" class="cp-action-approve" :disabled="deciding" @click="decide(true)">
					{{ deciding ? "En cours…" : block.approve_label || "Approuver" }}
				</button>
				<button type="button" class="cp-action-reject" :disabled="deciding" @click="decide(false)">Refuser</button>
				<span class="cp-action-note">Rien n'est fait avant votre approbation</span>
			</template>
			<template v-else-if="status === 'Executed'">
				<span class="cp-action-result">Fait.</span>
				<button v-if="hasLink" type="button" class="cp-action-link" @click="openDeskPath(resultHref)">{{ resultLabel }}</button>
			</template>
			<span v-else-if="status === 'Rejected'" class="cp-action-note">Proposition refusée. Rien n'a été fait.</span>
		</footer>
		<p v-if="message" class="cp-action-message" :class="{ 'is-bad': status === 'Failed' || open }" role="alert">{{ message }}</p>
	</section>
</template>

<style scoped>
.cp-action {
	border: 1px solid #e2e8f0;
	border-radius: 10px;
	overflow: hidden;
	background: #ffffff;
}
.cp-action-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	padding: 10px 12px;
	border-bottom: 1px solid #e2e8f0;
	background: #f8fafc;
}
.cp-action-title {
	margin: 0;
	font-size: 14px;
	font-weight: 650;
	color: #0f172a;
}
.cp-action-badge {
	flex: none;
	padding: 1px 8px;
	border-radius: 999px;
	font-size: 12px;
	white-space: nowrap;
}
.cp-action-badge.is-pending {
	color: #8a4b00;
	background: #fff7ed;
}
.cp-action-badge.is-done {
	color: #065f46;
	background: #ecfdf5;
}
.cp-action-badge.is-bad {
	color: #b42318;
	background: #fef3f2;
}
.cp-action-badge.is-muted {
	color: #475569;
	background: #f1f5f9;
}
.cp-action-sub {
	margin: 0;
	padding: 8px 12px 0;
	font-size: 13px;
	color: #64748b;
}
.cp-action-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 13.5px;
}
.cp-action-table td {
	padding: 7px 12px;
	border-bottom: 1px solid #e2e8f0;
	vertical-align: top;
}
.cp-action-label {
	color: #1e293b;
}
.cp-action-detail {
	display: block;
	font-size: 12px;
	color: #64748b;
}
.cp-action-value {
	text-align: right;
	white-space: nowrap;
	font-variant-numeric: tabular-nums;
	color: #1e293b;
}
.cp-action-total .cp-action-label {
	color: #64748b;
}
.cp-action-total.is-last td {
	border-bottom: 0;
	font-weight: 650;
	color: #0f172a;
}
.cp-action-foot {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	padding: 10px 12px;
	border-top: 1px solid #e2e8f0;
}
.cp-action-table + .cp-action-foot {
	border-top: 0;
}
.cp-action-approve,
.cp-action-reject,
.cp-action-link {
	height: 30px;
	padding: 0 14px;
	border-radius: 999px;
	font: inherit;
	font-size: 13px;
	cursor: pointer;
	transition: background-color 0.15s ease, border-color 0.15s ease, filter 0.15s ease;
}
.cp-action-approve {
	border: 1px solid #047857;
	background: #047857;
	color: #ffffff;
	font-weight: 600;
}
.cp-action-approve:hover:not(:disabled) {
	filter: brightness(0.95);
}
.cp-action-reject,
.cp-action-link {
	border: 1px solid #e2e8f0;
	background: transparent;
	color: #334155;
	font-weight: 500;
}
.cp-action-reject:hover:not(:disabled),
.cp-action-link:hover {
	border-color: #cbd5e1;
	background: #f8fafc;
	color: #0f172a;
}
.cp-action-approve:disabled,
.cp-action-reject:disabled {
	cursor: default;
	opacity: 0.6;
}
.cp-action-approve:focus-visible,
.cp-action-reject:focus-visible,
.cp-action-link:focus-visible {
	outline: 2px solid #047857;
	outline-offset: 2px;
}
.cp-action-note {
	margin-left: auto;
	font-size: 12px;
	color: #64748b;
}
.cp-action-result {
	font-size: 13px;
	font-weight: 600;
	color: #065f46;
}
.cp-action-message {
	margin: 0;
	padding: 0 12px 10px;
	font-size: 13px;
	color: #475569;
}
.cp-action-message.is-bad {
	color: #b42318;
}
@media (prefers-reduced-motion: reduce) {
	.cp-action-approve,
	.cp-action-reject,
	.cp-action-link {
		transition: none;
	}
}
</style>
