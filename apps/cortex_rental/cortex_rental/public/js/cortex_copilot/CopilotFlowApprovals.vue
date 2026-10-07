<script setup>
// Questionnaire « Approbations » : liste (en attente / toutes) et décision dans la conversation, seulement si la personne y est autorisée.
// Les règles sont celles du serveur (ni sa propre demande, ni auto-approbation par défaut). L'assistant ne décide jamais.
import { ref, onMounted } from "vue";
import CopilotFlowShell from "./CopilotFlowShell.vue";
import { apiCall } from "./chatClient.js";

const filter = ref("pending");
const items = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref("");
const done = ref(""); // dernier résultat de décision, affiché sous la liste

const open = ref(null); // id de la demande examinée
const options = ref({}); // id → { can_approve, can_reject, can_withdraw, note }
const mode = ref(""); // « approve » | « reject » | « withdraw »
const reason = ref("");
const busy = ref(false);
const decisionError = ref("");

const STATUS = { pending: "En attente", approved: "Approuvée", rejected: "Refusée", withdrawn: "Retirée", expired: "Expirée" };

const when = (value) => {
	const date = new Date(String(value || "").replace(" ", "T"));
	return Number.isNaN(date.getTime()) ? "" : date.toLocaleString("fr-CA", { dateStyle: "medium", timeStyle: "short" });
};
// Sans nom complet côté serveur, on présente l'adresse lisiblement (« marie.dupont@… » → « Marie Dupont »).
const who = (value) =>
	value && value.includes("@")
		? value
				.split("@")[0]
				.replace(/[._]/g, " ")
				.replace(/\b\p{L}/gu, (c) => c.toUpperCase())
		: value || "—";

async function load() {
	loading.value = true;
	error.value = "";
	try {
		const data = await apiCall("cortex_rental.api.v1.approval_queue.list_approval_requests", { status: filter.value, page_size: 10 });
		items.value = data.items || [];
		total.value = data.total_count || items.value.length;
	} catch (e) {
		error.value = e.message;
		items.value = [];
	} finally {
		loading.value = false;
	}
}

onMounted(load);

function setFilter(value) {
	if (filter.value === value) return;
	filter.value = value;
	close();
	load();
}

async function examine(item) {
	if (open.value === item.id) return close();
	open.value = item.id;
	mode.value = "";
	reason.value = "";
	decisionError.value = "";
	if (!options.value[item.id]) {
		try {
			options.value = { ...options.value, [item.id]: await apiCall("cortex_rental.api.v1.approval_queue.decision_options", { name: item.id }) };
		} catch (e) {
			decisionError.value = e.message;
		}
	}
}

function close() {
	open.value = null;
	mode.value = "";
	reason.value = "";
	decisionError.value = "";
}

function choose(value) {
	mode.value = value;
	reason.value = "";
	decisionError.value = "";
}

const needsReason = () => mode.value === "reject";

async function confirm(item) {
	decisionError.value = "";
	if (needsReason() && reason.value.trim().length < 3) return (decisionError.value = "Un motif d'au moins trois caractères est obligatoire pour refuser.");
	busy.value = true;
	try {
		await apiCall("cortex_rental.api.v1.approval_queue.decide_approval", { name: item.id, decision: mode.value, reason: reason.value.trim() }, "POST");
		const verb = { approve: "approuvée", reject: "refusée", withdraw: "retirée" }[mode.value];
		done.value = `Demande ${item.reference_name || item.id} ${verb}. La décision est consignée à votre nom.`;
		close();
		await load();
	} catch (e) {
		decisionError.value = e.message;
	} finally {
		busy.value = false;
	}
}

function openRecord(item) {
	frappe.set_route("Form", "Approval Request", item.id);
}
function openAll() {
	frappe.set_route("List", "Approval Request");
}
</script>

<template>
	<CopilotFlowShell
		title="Demandes d'approbation"
		subtitle="Un humain décide de chaque demande. L'assistant ne les approuve jamais, et vous ne pouvez pas décider de votre propre demande."
		:error="error"
	>
		<div class="p-step">
			<div class="p-seg" role="radiogroup" aria-label="Filtrer les demandes">
				<button type="button" role="radio" :aria-checked="filter === 'pending'" :class="{ on: filter === 'pending' }" @click="setFilter('pending')">En attente</button>
				<button type="button" role="radio" :aria-checked="filter === 'all'" :class="{ on: filter === 'all' }" @click="setFilter('all')">Toutes</button>
			</div>

			<p v-if="done" class="p-done" role="status"><span class="p-ok">✓</span>{{ done }}</p>

			<p v-if="loading" class="p-empty">Chargement des demandes…</p>
			<p v-else-if="!items.length && !error" class="p-empty">{{ filter === "pending" ? "Aucune demande en attente de décision." : "Aucune demande pour le moment." }}</p>

			<ul v-if="items.length" class="p-list">
				<li v-for="item in items" :key="item.id" class="p-item" :class="{ open: open === item.id }">
					<div class="p-line">
						<div class="p-main">
							<strong>{{ item.title }}</strong>
							<span class="p-meta">{{ item.reference_name || item.id }} · demandée par {{ who(item.requested_by) }} · {{ when(item.created_at) }}</span>
						</div>
						<span class="p-badge" :class="item.status">{{ STATUS[item.status] || item.status }}</span>
						<button v-if="item.status === 'pending'" type="button" class="p-link" :aria-expanded="open === item.id" @click="examine(item)">{{ open === item.id ? "Fermer" : "Examiner" }}</button>
						<button v-else type="button" class="p-link" @click="openRecord(item)">Ouvrir</button>
					</div>

					<div v-if="open === item.id" class="p-detail">
						<p v-if="item.description" class="p-desc">{{ item.description }}</p>
						<p v-if="item.rejection_reason" class="p-desc">Motif du refus : {{ item.rejection_reason }}</p>
						<template v-if="options[item.id]">
							<p v-if="options[item.id].note" class="p-note">{{ options[item.id].note }}</p>
							<div v-if="!mode" class="p-actions">
								<button v-if="options[item.id].can_approve" type="button" class="cx-btn cx-btn-primary" @click="choose('approve')">Approuver</button>
								<button v-if="options[item.id].can_reject" type="button" class="cx-btn cx-btn-secondary p-danger" @click="choose('reject')">Refuser</button>
								<button v-if="options[item.id].can_withdraw" type="button" class="cx-btn cx-btn-secondary" @click="choose('withdraw')">Retirer ma demande</button>
								<button type="button" class="cx-btn cx-btn-secondary" @click="openRecord(item)">Ouvrir la fiche</button>
								<span v-if="!options[item.id].can_approve && !options[item.id].can_reject && !options[item.id].can_withdraw" class="p-hint">Vous ne pouvez pas décider de cette demande.</span>
							</div>
							<div v-else class="p-confirm">
								<p class="p-ask">
									{{ mode === "approve" ? "Confirmer l'approbation ?" : mode === "reject" ? "Confirmer le refus ?" : "Retirer cette demande ?" }}
									<span class="p-hint">La décision sera consignée à votre nom, avec l'heure.</span>
								</p>
								<label class="p-field">
									<span class="p-label">{{ mode === "reject" ? "Motif (obligatoire)" : "Motif (facultatif)" }}</span>
									<textarea v-model="reason" class="p-input" rows="2" maxlength="500" :aria-invalid="!!decisionError"></textarea>
								</label>
								<div class="p-actions">
									<button type="button" class="cx-btn cx-btn-primary" :class="{ 'p-danger-fill': mode === 'reject' }" :disabled="busy" @click="confirm(item)">
										{{ busy ? "Enregistrement…" : mode === "approve" ? "Oui, approuver" : mode === "reject" ? "Oui, refuser" : "Oui, retirer" }}
									</button>
									<button type="button" class="cx-btn cx-btn-secondary" :disabled="busy" @click="mode = ''">Annuler</button>
								</div>
							</div>
						</template>
						<p v-else-if="!decisionError" class="p-hint">Chargement…</p>
						<p v-if="decisionError" class="p-err" role="alert">{{ decisionError }}</p>
					</div>
				</li>
			</ul>
			<p v-if="total > items.length" class="p-hint">{{ items.length }} demandes affichées sur {{ total }}.</p>
		</div>
		<template #footer>
			<button type="button" class="cx-btn cx-btn-secondary" @click="openAll">Ouvrir la liste complète</button>
			<button type="button" class="cx-btn cx-btn-secondary" :disabled="loading" @click="load">Actualiser</button>
		</template>
	</CopilotFlowShell>
</template>

<style scoped>
.p-step {
	display: grid;
	gap: 12px;
}
.p-seg {
	display: inline-flex;
	gap: 6px;
}
.p-seg button {
	height: 34px;
	padding: 0 14px;
	border: 1px solid #e0dfda;
	border-radius: 999px;
	background: #fff;
	font-size: 13.5px;
	cursor: pointer;
	transition: background-color 0.15s ease, border-color 0.15s ease;
}
.p-seg button.on {
	border-color: #047857;
	background: #f1faf5;
	color: #066336;
	font-weight: 600;
}
.p-list {
	display: grid;
	gap: 6px;
	margin: 0;
	padding: 0;
	list-style: none;
}
.p-item {
	border: 1px solid #efeeea;
	border-radius: 12px;
	transition: border-color 0.15s ease, background-color 0.15s ease;
}
.p-item.open {
	border-color: #cfd9d3;
	background: #fbfcfb;
}
.p-line {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto auto;
	align-items: center;
	gap: 6px 12px;
	padding: 10px 12px;
}
.p-main {
	display: grid;
	min-width: 0;
}
.p-main strong {
	font-size: 13.5px;
	font-weight: 600;
}
.p-meta {
	font-size: 12px;
	color: #6b6a66;
}
.p-badge {
	padding: 2px 9px;
	border-radius: 999px;
	background: #ecebe6;
	color: #55544f;
	font-size: 11.5px;
	font-weight: 600;
	white-space: nowrap;
}
.p-badge.pending {
	background: #fdf1de;
	color: #8a4b00;
}
.p-badge.approved {
	background: #e7f6ee;
	color: #066336;
}
.p-badge.rejected {
	background: #fbeaea;
	color: #b42318;
}
.p-link {
	padding: 0 4px;
	border: 0;
	background: none;
	color: #066336;
	font-size: 13px;
	font-weight: 600;
	cursor: pointer;
}
.p-detail {
	display: grid;
	gap: 10px;
	padding: 4px 12px 12px;
	animation: p-in 0.2s ease both;
}
@keyframes p-in {
	from {
		opacity: 0;
		transform: translateY(-4px);
	}
	to {
		opacity: 1;
		transform: none;
	}
}
.p-desc {
	margin: 0;
	font-size: 13px;
	color: #3a3a37;
}
.p-note {
	margin: 0;
	padding: 8px 11px;
	border-radius: 9px;
	background: #f4f3ef;
	font-size: 12.5px;
	color: #55544f;
}
.p-actions {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
}
.p-confirm {
	display: grid;
	gap: 10px;
}
.p-ask {
	margin: 0;
	display: grid;
	gap: 2px;
	font-size: 13.5px;
	font-weight: 600;
}
.p-hint {
	font-size: 12.5px;
	font-weight: 400;
	color: #6b6a66;
}
.p-field {
	display: grid;
	gap: 5px;
}
.p-label {
	font-size: 12.5px;
	font-weight: 600;
	color: #55544f;
}
.p-input {
	width: 100%;
	padding: 8px 10px;
	border: 1px solid #e0dfda;
	border-radius: 9px;
	font: inherit;
	font-size: 14px;
	resize: vertical;
}
.p-input:focus {
	border-color: #047857;
	box-shadow: 0 0 0 3px rgba(4, 120, 87, 0.12);
	outline: none;
}
.p-danger {
	color: #b42318;
}
.p-danger-fill {
	background: #b42318 !important;
	border-color: #b42318 !important;
}
.p-err {
	margin: 0;
	padding: 8px 11px;
	border-radius: 9px;
	background: #fbeaea;
	color: #b42318;
	font-size: 13px;
}
.p-empty {
	margin: 0;
	font-size: 13.5px;
	color: #6b6a66;
}
.p-done {
	display: flex;
	align-items: center;
	gap: 8px;
	margin: 0;
	padding: 9px 12px;
	border-radius: 10px;
	background: #f1faf5;
	color: #066336;
	font-size: 13.5px;
}
.p-ok {
	display: inline-grid;
	place-items: center;
	flex: none;
	width: 20px;
	height: 20px;
	border-radius: 50%;
	background: #047857;
	color: #fff;
	font-size: 11px;
}
@media (max-width: 640px) {
	.p-line {
		grid-template-columns: minmax(0, 1fr) auto;
	}
	.p-link {
		justify-self: start;
	}
}
@media (prefers-reduced-motion: reduce) {
	.p-detail {
		animation: none;
	}
}
</style>
