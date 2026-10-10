<script setup>
// Questionnaire « Nouvelle location » : client → dates → équipement (disponibilité calculée par le serveur) → récapitulatif.
// Rien n'est créé avant « Créer le devis » ; le prix est celui du serveur (règle 7 = 3 comprise).
import { ref, computed, onMounted } from "vue";
import CopilotFlowShell from "./CopilotFlowShell.vue";
import { apiCall, money, toServerDate } from "./chatClient.js";

const props = defineProps({
	preselect: { type: Array, default: () => [] }, // codes d'équipement déjà choisis
	starts: { type: String, default: "" }, // « AAAA-MM-JJTHH:mm » si les dates sont déjà connues
	ends: { type: String, default: "" },
});
const emit = defineEmits(["done"]);

const STEPS = ["Client", "Dates", "Équipement", "Récapitulatif"];
const step = ref(1);
const error = ref("");
const busy = ref(false);

// 1. Client
const customers = ref([]);
const customerQuery = ref("");
const customer = ref(null);
const newName = ref("");
const showNew = ref(false);
const filteredCustomers = computed(() => {
	const q = customerQuery.value.trim().toLowerCase();
	return customers.value.filter((c) => !q || c.name.toLowerCase().includes(q)).slice(0, 8);
});

// 2. Dates
const starts = ref(props.starts);
const ends = ref(props.ends);
const periodError = computed(() => {
	if (!starts.value || !ends.value) return "Indiquez le début et la fin de la location.";
	if (ends.value <= starts.value) return "La fin doit être après le début.";
	return "";
});

// 3. Équipement
const catalog = ref([]);
const search = ref("");
const qty = ref({}); // item_code → quantité choisie
const groups = computed(() => {
	const q = search.value.trim().toLowerCase();
	const map = {};
	for (const row of catalog.value) {
		if (q && !row.item_name.toLowerCase().includes(q) && !row.item_code.toLowerCase().includes(q)) continue;
		(map[row.category || "Autre"] = map[row.category || "Autre"] || []).push(row);
	}
	return Object.entries(map).sort(([a], [b]) => a.localeCompare(b, "fr"));
});
const chosen = computed(() => catalog.value.filter((r) => (qty.value[r.item_code] || 0) > 0));

// 4. Récapitulatif
const pricing = ref(null);
const created = ref(null);

const STATUS = { ok: "Libre", partial: "Partiellement pris", full: "Complet", none: "Aucun au parc" };

onMounted(async () => {
	try {
		const data = await apiCall("cortex_rental.api.v1.rentals.search_rental_customers", {});
		customers.value = data.items || [];
	} catch (e) {
		error.value = e.message;
	}
});

const when = (local) => (local ? new Date(local).toLocaleString("fr-CA", { dateStyle: "medium", timeStyle: "short" }) : "");
const days = (value) => new Intl.NumberFormat("fr-CA", { maximumFractionDigits: 2 }).format(Number(value || 0));

function pick(c) {
	customer.value = c;
	error.value = "";
}

async function createCustomer() {
	error.value = "";
	busy.value = true;
	try {
		const data = await apiCall("cortex_rental.api.v1.customers.create_customer", { customer_name: newName.value }, "POST");
		customer.value = { id: data.id, name: data.name };
		customers.value.unshift(customer.value);
		showNew.value = false;
		newName.value = "";
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}

function toDateOnly(local) {
	return local.slice(0, 10);
}

async function loadCatalog() {
	busy.value = true;
	error.value = "";
	try {
		const data = await apiCall("cortex_rental.api.v1.availability.get_period_summary", {
			starts_at: toDateOnly(starts.value),
			ends_at: toDateOnly(ends.value),
		});
		const rates = await apiCall("cortex_rental.api.v1.rentals.search_rental_catalog", {});
		const rateOf = Object.fromEntries((rates.items || []).map((r) => [r.item_code, r.daily_rate]));
		catalog.value = (data.items || []).map((r) => ({ ...r, daily_rate: rateOf[r.item_code] }));
		for (const code of props.preselect) if (catalog.value.some((r) => r.item_code === code && r.free > 0)) qty.value[code] = qty.value[code] || 1;
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}

function setQty(row, value) {
	const n = Math.max(0, Math.min(Number(value) || 0, row.free));
	qty.value = { ...qty.value, [row.item_code]: n };
}

async function loadPricing() {
	busy.value = true;
	error.value = "";
	try {
		pricing.value = await apiCall(
			"cortex_rental.api.v1.rentals.preview_pricing",
			{
				starts_at: toServerDate(starts.value),
				ends_at: toServerDate(ends.value),
				items: JSON.stringify(chosen.value.map((r) => ({ item_code: r.item_code, quantity: qty.value[r.item_code] }))),
			},
			"POST"
		);
	} catch (e) {
		error.value = e.message;
		return false;
	} finally {
		busy.value = false;
	}
	return true;
}

async function next() {
	error.value = "";
	if (step.value === 1) {
		if (!customer.value) return (error.value = "Choisissez un client ou créez-en un.");
		step.value = 2;
	} else if (step.value === 2) {
		if (periodError.value) return (error.value = periodError.value);
		await loadCatalog();
		if (!error.value) step.value = 3;
	} else if (step.value === 3) {
		if (!chosen.value.length) return (error.value = "Choisissez au moins un équipement.");
		if (await loadPricing()) step.value = 4;
	}
}

function back() {
	error.value = "";
	if (step.value > 1) step.value -= 1;
}

async function create() {
	busy.value = true;
	error.value = "";
	try {
		const result = await apiCall(
			"cortex_rental.api.v1.rentals.create_quote_draft",
			{
				customer_id: customer.value.id,
				starts_at: toServerDate(starts.value),
				ends_at: toServerDate(ends.value),
				items: JSON.stringify(chosen.value.map((r) => ({ item_code: r.item_code, quantity: qty.value[r.item_code] }))),
				notes: "Préparé avec l'assistant Cortex.",
			},
			"POST"
		);
		const name = result.entity_id;
		let hold = { hold_status: "", hold_until: "", hold_note: "" };
		try {
			hold = await apiCall("frappe.client.get_value", { doctype: "Cortex Rental Transaction", fieldname: JSON.stringify(["hold_status", "hold_until", "hold_note"]), filters: name });
		} catch (e) {
			// La lecture de la retenue ne change rien au devis créé : on le dit simplement.
		}
		created.value = { name, hold };
		emit("done", name);
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}

const holdMessage = computed(() => {
	const hold = (created.value && created.value.hold) || {};
	if (hold.hold_status === "Active") return `Le matériel est retenu jusqu'au ${(hold.hold_until || "").slice(0, 16).replace("T", " ")}.`;
	if (hold.hold_status === "Insufficient") return hold.hold_note || "Aucune retenue : la disponibilité n'a pas suffi.";
	return "Aucune retenue du matériel n'a été prise pour ce devis.";
});

function open() {
	frappe.set_route("Form", "Cortex Rental Transaction", created.value.name);
}
</script>

<template>
	<CopilotFlowShell
		v-if="!created"
		title="Nouvelle location"
		subtitle="Quelques questions, puis le devis est créé en brouillon. Le prix et la disponibilité viennent du serveur."
		:steps="STEPS"
		:step="step"
		:error="error"
	>
		<!-- 1. Client -->
		<div v-if="step === 1" class="q-step">
			<label class="q-label" for="q-client">Pour quel client ?</label>
			<input id="q-client" v-model="customerQuery" class="q-input" type="search" placeholder="Rechercher un client…" autocomplete="off" />
			<ul class="q-list" aria-label="Clients">
				<li v-for="c in filteredCustomers" :key="c.id">
					<button type="button" class="q-row" :class="{ on: customer && customer.id === c.id }" :aria-pressed="!!(customer && customer.id === c.id)" @click="pick(c)">
						<span>{{ c.name }}</span>
						<span v-if="customer && customer.id === c.id" class="q-check">✓</span>
					</button>
				</li>
				<li v-if="!filteredCustomers.length" class="q-empty">Aucun client ne correspond.</li>
			</ul>
			<div class="q-new">
				<button v-if="!showNew" type="button" class="q-link" @click="showNew = true">+ Nouveau client</button>
				<form v-else class="q-inline" @submit.prevent="createCustomer">
					<input v-model="newName" class="q-input" placeholder="Nom du nouveau client" aria-label="Nom du nouveau client" maxlength="140" />
					<button type="submit" class="cx-btn cx-btn-secondary" :disabled="busy || newName.trim().length < 2">Créer le client</button>
					<button type="button" class="q-link" @click="showNew = false">Annuler</button>
				</form>
			</div>
		</div>

		<!-- 2. Dates -->
		<div v-else-if="step === 2" class="q-step">
			<p class="q-who">Client : <strong>{{ customer.name }}</strong></p>
			<div class="q-dates">
				<label class="q-field"><span class="q-label">Début</span><input v-model="starts" class="q-input" type="datetime-local" step="900" /></label>
				<label class="q-field"><span class="q-label">Fin</span><input v-model="ends" class="q-input" type="datetime-local" step="900" /></label>
			</div>
			<p class="q-hint">La disponibilité de l'étape suivante est calculée pour ces dates.</p>
		</div>

		<!-- 3. Équipement -->
		<div v-else-if="step === 3" class="q-step">
			<input v-model="search" class="q-input" type="search" placeholder="Filtrer l'équipement…" aria-label="Filtrer l'équipement" />
			<div class="q-groups">
				<div v-for="[category, rows] in groups" :key="category" class="q-group">
					<h4 class="q-cat">{{ category }}</h4>
					<div v-for="row in rows" :key="row.item_code" class="q-item" :class="{ out: row.free <= 0 }">
						<div class="q-item-main">
							<strong>{{ row.item_name }}</strong>
							<span class="q-meta">{{ row.item_code }} · {{ row.daily_rate != null ? money(row.daily_rate) + " / jour" : "" }}</span>
						</div>
						<span class="q-badge" :class="row.status">{{ row.free > 0 ? `${row.free} libre${row.free > 1 ? "s" : ""} sur ${row.fleet}` : STATUS[row.status] }}</span>
						<div class="q-qty" role="group" :aria-label="`Quantité de ${row.item_name}`">
							<button type="button" :disabled="row.free <= 0 || !(qty[row.item_code] > 0)" aria-label="Moins" @click="setQty(row, (qty[row.item_code] || 0) - 1)">−</button>
							<input :value="qty[row.item_code] || 0" type="number" min="0" :max="row.free" :disabled="row.free <= 0" aria-label="Quantité" @input="setQty(row, $event.target.value)" />
							<button type="button" :disabled="row.free <= 0 || (qty[row.item_code] || 0) >= row.free" aria-label="Plus" @click="setQty(row, (qty[row.item_code] || 0) + 1)">+</button>
						</div>
					</div>
				</div>
				<p v-if="!groups.length" class="q-empty">Aucun équipement ne correspond.</p>
			</div>
			<p class="q-hint">{{ chosen.length }} équipement{{ chosen.length > 1 ? "s" : "" }} choisi{{ chosen.length > 1 ? "s" : "" }}. Un article complet ne peut pas être ajouté.</p>
		</div>

		<!-- 4. Récapitulatif -->
		<div v-else class="q-step">
			<p class="q-who">
				<strong>{{ customer.name }}</strong> · du {{ when(starts) }} au {{ when(ends) }}
				<span v-if="pricing"> · {{ pricing.calendar_days }} jour(s) civils, {{ days(pricing.billable_days) }} jour(s) facturé(s)</span>
			</p>
			<table v-if="pricing" class="q-table">
				<thead><tr><th>Équipement</th><th class="r">Qté</th><th class="r">Tarif / jour</th><th class="r">Montant</th></tr></thead>
				<tbody>
					<tr v-for="line in pricing.lines" :key="line.item_code">
						<td>{{ line.item_name }}</td><td class="r">{{ line.quantity }}</td><td class="r">{{ money(line.daily_rate) }}</td><td class="r">{{ money(line.line_subtotal) }}</td>
					</tr>
				</tbody>
				<tfoot><tr><td colspan="3">Sous-total (avant taxes)</td><td class="r"><strong>{{ money(pricing.subtotal) }}</strong></td></tr></tfoot>
			</table>
			<p class="q-hint">Le devis est créé en brouillon : le matériel est retenu s'il est libre, rien n'est envoyé au client.</p>
		</div>

		<template #footer>
			<button v-if="step > 1" type="button" class="cx-btn cx-btn-secondary" :disabled="busy" @click="back">Retour</button>
			<button v-if="step < 4" type="button" class="cx-btn cx-btn-primary q-next" :disabled="busy" @click="next">{{ busy ? "Un instant…" : "Continuer" }}</button>
			<button v-else type="button" class="cx-btn cx-btn-primary q-next" :disabled="busy" @click="create">{{ busy ? "Création…" : "Créer le devis" }}</button>
		</template>
	</CopilotFlowShell>

	<CopilotFlowShell v-else title="Devis créé" :subtitle="created.name">
		<p class="q-done">
			<span class="q-ok">✓</span>
			Le devis <strong>{{ created.name }}</strong> est créé pour {{ customer.name }}.
			{{ holdMessage }}
		</p>
		<template #footer>
			<button type="button" class="cx-btn cx-btn-primary" @click="open">Ouvrir le devis</button>
		</template>
	</CopilotFlowShell>
</template>

<style scoped>
.q-step {
	display: grid;
	gap: 10px;
}
.q-label {
	font-size: 12.5px;
	font-weight: var(--cx-weight-strong, 600);
	color: #55544f;
}
.q-input {
	width: 100%;
	height: 38px;
	padding: 0 10px;
	border: 1px solid #e0dfda;
	border-radius: 9px;
	background: #fff;
	font-size: 14px;
	transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.q-input:focus {
	border-color: #047857;
	box-shadow: 0 0 0 3px rgba(4, 120, 87, 0.12);
	outline: none;
}
.q-list {
	display: grid;
	gap: 4px;
	margin: 0;
	padding: 0;
	list-style: none;
}
.q-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	width: 100%;
	padding: 9px 12px;
	border: 1px solid #efeeea;
	border-radius: 10px;
	background: #fff;
	font-size: 14px;
	text-align: left;
	cursor: pointer;
	transition: background-color 0.15s ease, border-color 0.15s ease;
}
.q-row:hover {
	background: #f7f7f5;
}
.q-row.on {
	border-color: #047857;
	background: #f1faf5;
}
.q-check {
	color: #047857;
	font-weight: var(--cx-weight-heavy, 700);
}
.q-empty {
	padding: 8px 2px;
	font-size: 13px;
	color: #6b6a66;
}
.q-new {
	margin-top: 2px;
}
.q-inline {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
}
.q-inline .q-input {
	flex: 1 1 220px;
	width: auto;
}
.q-link {
	padding: 0;
	border: 0;
	background: none;
	color: #066336;
	font-size: 13px;
	font-weight: var(--cx-weight-strong, 600);
	cursor: pointer;
}
.q-who {
	margin: 0;
	font-size: 13.5px;
	color: #3a3a37;
}
.q-dates {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}
.q-field {
	display: grid;
	gap: 5px;
}
.q-hint {
	margin: 0;
	font-size: 12.5px;
	color: #6b6a66;
}
.q-groups {
	display: grid;
	gap: 12px;
	max-height: 360px;
	overflow-y: auto;
	padding-right: 2px;
}
.q-cat {
	margin: 0 0 6px;
	font-size: 11.5px;
	font-weight: var(--cx-weight-heavy, 700);
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: #6b6a66;
}
.q-item {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto auto;
	align-items: center;
	gap: 6px 12px;
	padding: 9px 12px;
	margin-bottom: 4px;
	border: 1px solid #efeeea;
	border-radius: 10px;
}
.q-item.out {
	opacity: 0.6;
}
.q-item-main {
	display: grid;
	min-width: 0;
}
.q-item-main strong {
	font-size: 13.5px;
	font-weight: var(--cx-weight-strong, 600);
}
.q-meta {
	font-size: 12px;
	color: #6b6a66;
}
.q-badge {
	padding: 2px 9px;
	border-radius: 999px;
	background: #e7f6ee;
	color: #066336;
	font-size: 11.5px;
	font-weight: var(--cx-weight-strong, 600);
	white-space: nowrap;
}
.q-badge.partial {
	background: #fdf1de;
	color: #8a4b00;
}
.q-badge.full,
.q-badge.none {
	background: #fbeaea;
	color: #b42318;
}
.q-qty {
	display: inline-flex;
	align-items: center;
	border: 1px solid #e0dfda;
	border-radius: 9px;
	overflow: hidden;
}
.q-qty button {
	width: 28px;
	height: 30px;
	border: 0;
	background: #f7f7f5;
	font-size: 15px;
	cursor: pointer;
}
.q-qty button:disabled {
	opacity: 0.4;
	cursor: not-allowed;
}
.q-qty input {
	width: 40px;
	height: 30px;
	border: 0;
	border-inline: 1px solid #e0dfda;
	text-align: center;
	font-size: 13.5px;
}
.q-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 13.5px;
}
.q-table th,
.q-table td {
	padding: 8px 10px;
	border-bottom: 1px solid #efeeea;
	text-align: left;
}
.q-table .r {
	text-align: right;
	font-variant-numeric: tabular-nums;
}
.q-table tfoot td {
	border-bottom: 0;
	color: #3a3a37;
}
.q-done {
	margin: 0;
	font-size: 14px;
}
.q-ok {
	display: inline-grid;
	place-items: center;
	width: 22px;
	height: 22px;
	margin-right: 6px;
	border-radius: 50%;
	background: #047857;
	color: #fff;
	font-size: 12px;
}
.q-next {
	margin-left: auto;
}
@media (max-width: 640px) {
	.q-dates {
		grid-template-columns: minmax(0, 1fr);
	}
	.q-item {
		grid-template-columns: minmax(0, 1fr) auto;
	}
	.q-item .q-qty {
		grid-column: 1 / -1;
		justify-self: start;
	}
}
</style>
