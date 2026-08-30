<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { fmtDateTime, addDays } from "../cortex_shared/dateUtils.js";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexStatusBadge from "../cortex_shared/CortexStatusBadge.vue";
import CortexErrorState from "../cortex_shared/CortexErrorState.vue";
import CortexEmptyState from "../cortex_shared/CortexEmptyState.vue";

// ---------------------------------------------------------------------
// State
// ---------------------------------------------------------------------
const customer = ref(null); // {id, name}
const customerSearch = ref("");
const customerResults = ref([]);
const customerSearchLoading = ref(false);
const showNewCustomerForm = ref(false);
const newCustomer = reactive({ customer_name: "", email: "", phone: "" });
const newCustomerSaving = ref(false);
const newCustomerError = ref("");

const now = new Date();
const startsAt = ref(fmtLocalInput(now));
const endsAt = ref(fmtLocalInput(addDays(now, 1)));

const itemSearch = ref("");
const itemResults = ref([]);
const itemSearchLoading = ref(false);
const lines = ref([]); // {item_id, name, category, quantity, unit_rate, discount_percentage, availability}

const notes = ref("");

const pricing = ref(null); // {calendar_days, billable_days, subtotal, total, lines}
const pricingLoading = ref(false);
const pricingError = ref("");

const submitting = ref(false);
const submitError = ref("");

let itemSearchDebounce = null;
let customerSearchDebounce = null;
let pricingDebounce = null;
let availabilityDebounce = null;

// ---------------------------------------------------------------------
// Prefill from Availability's "Créer une soumission" button — the real
// Frappe cross-page pattern (frappe.route_options), not a URL query
// string. Cleared immediately after reading so a later, unrelated
// navigation to this page doesn't silently reuse stale dates.
// ---------------------------------------------------------------------
onMounted(() => {
	if (frappe.route_options) {
		if (frappe.route_options.starts_at) startsAt.value = fmtLocalInput(new Date(frappe.route_options.starts_at));
		if (frappe.route_options.ends_at) endsAt.value = fmtLocalInput(new Date(frappe.route_options.ends_at));
		frappe.route_options = null;
	}
	refreshPricing();
});

function fmtLocalInput(d) {
	const pad = (n) => String(n).padStart(2, "0");
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function debounce(fn, ms) {
	let handle;
	return (...args) => {
		clearTimeout(handle);
		handle = setTimeout(() => fn(...args), ms);
	};
}

// ---------------------------------------------------------------------
// Customer search / create — real cortex_rental.api.v1.customers calls
// ---------------------------------------------------------------------
function searchCustomers() {
	if (!customerSearch.value.trim()) {
		customerResults.value = [];
		return;
	}
	customerSearchLoading.value = true;
	frappe.call({
		method: "cortex_rental.api.v1.customers.search_customers",
		type: "GET",
		args: { query: customerSearch.value.trim() },
		callback(r) {
			customerSearchLoading.value = false;
			customerResults.value = (r.message && r.message.data) || [];
		},
		error() {
			customerSearchLoading.value = false;
		},
	});
}
watch(customerSearch, debounce(searchCustomers, 300));

function selectCustomer(c) {
	customer.value = c;
	customerResults.value = [];
	customerSearch.value = "";
	showNewCustomerForm.value = false;
}

function clearCustomer() {
	customer.value = null;
}

function createCustomerDraft() {
	if (!newCustomer.customer_name.trim()) return;
	newCustomerSaving.value = true;
	newCustomerError.value = "";
	frappe.call({
		method: "cortex_rental.api.v1.customers.create_customer_draft",
		type: "POST",
		args: { ...newCustomer },
		callback(r) {
			newCustomerSaving.value = false;
			const data = r.message && r.message.data;
			if (data) {
				selectCustomer({ id: data.id, name: data.customer_name });
				newCustomer.customer_name = "";
				newCustomer.email = "";
				newCustomer.phone = "";
			}
		},
		error(r) {
			newCustomerSaving.value = false;
			newCustomerError.value =
				(r && r.responseJSON && (r.responseJSON.message || r.responseJSON.exc)) ||
				"Impossible de créer le client.";
		},
	});
}

// ---------------------------------------------------------------------
// Item search / add line — real cortex_rental.api.v1.items calls
// ---------------------------------------------------------------------
function searchItems() {
	if (!itemSearch.value.trim()) {
		itemResults.value = [];
		return;
	}
	itemSearchLoading.value = true;
	frappe.call({
		method: "cortex_rental.api.v1.items.search_items",
		type: "GET",
		args: { query: itemSearch.value.trim() },
		callback(r) {
			itemSearchLoading.value = false;
			itemResults.value = (r.message && r.message.data) || [];
		},
		error() {
			itemSearchLoading.value = false;
		},
	});
}
watch(itemSearch, debounce(searchItems, 300));

function addLine(item) {
	if (lines.value.some((l) => l.item_id === item.item_code)) return; // already on the quote
	lines.value.push({
		item_id: item.item_code,
		name: item.name,
		category: item.category,
		quantity: 1,
		unit_rate: item.daily_rate || 0,
		discount_percentage: 0,
		availability: null,
	});
	itemSearch.value = "";
	itemResults.value = [];
	onLinesChanged();
}

function removeLine(index) {
	lines.value.splice(index, 1);
	onLinesChanged();
}

function onLinesChanged() {
	debouncedPricing();
	debouncedAvailability();
}
watch([startsAt, endsAt], onLinesChanged);

// ---------------------------------------------------------------------
// Live pricing preview — always server-computed (PricingService), the
// design system explicitly forbids replicating the billable-days curve
// in JavaScript. See api/v1/quotes.py::preview_pricing.
// ---------------------------------------------------------------------
function refreshPricing() {
	if (!lines.value.length || !startsAt.value || !endsAt.value) {
		pricing.value = null;
		return;
	}
	pricingLoading.value = true;
	pricingError.value = "";
	frappe.call({
		method: "cortex_rental.api.v1.quotes.preview_pricing",
		type: "POST",
		args: {
			starts_at: fmtDateTime(new Date(startsAt.value)),
			ends_at: fmtDateTime(new Date(endsAt.value)),
			lines: JSON.stringify(
				lines.value.map((l) => ({
					item_id: l.item_id,
					quantity: l.quantity,
					unit_rate: l.unit_rate,
					discount_percentage: l.discount_percentage,
				})),
			),
		},
		callback(r) {
			pricingLoading.value = false;
			pricing.value = (r.message && r.message.data) || null;
		},
		error(r) {
			pricingLoading.value = false;
			pricingError.value =
				(r && r.responseJSON && (r.responseJSON.message || r.responseJSON.exc)) ||
				"Impossible de calculer le prix.";
		},
	});
}
const debouncedPricing = debounce(refreshPricing, 400);

// ---------------------------------------------------------------------
// Live availability per line — real cortex_rental.api.v1.availability
// (the agent-facing check_availability tool; human staff are also
// allowed by require_agent_scope's HUMAN_STAFF_ROLES bypass).
// ---------------------------------------------------------------------
function checkAvailability() {
	if (!lines.value.length || !startsAt.value || !endsAt.value) return;
	frappe.call({
		method: "cortex_rental.api.v1.availability.check_availability",
		type: "POST",
		args: {
			starts_at: fmtDateTime(new Date(startsAt.value)),
			ends_at: fmtDateTime(new Date(endsAt.value)),
			items: JSON.stringify(lines.value.map((l) => ({ item_id: l.item_id, quantity: l.quantity }))),
		},
		callback(r) {
			const results = (r.message && r.message.data) || [];
			for (const line of lines.value) {
				const match = results.find((res) => res.item_id === line.item_id);
				line.availability = match || null;
			}
		},
	});
}
const debouncedAvailability = debounce(checkAvailability, 500);

watch(
	() => lines.value.map((l) => `${l.quantity}:${l.unit_rate}:${l.discount_percentage}`).join("|"),
	() => onLinesChanged(),
);

// ---------------------------------------------------------------------
// Submit — real create_quote_draft call, then real navigation to the
// created Cortex Rental Transaction's Frappe Form (not a fabricated
// confirmation screen).
// ---------------------------------------------------------------------
const canSubmit = computed(() => customer.value && lines.value.length > 0 && startsAt.value && endsAt.value);

function submit() {
	if (!canSubmit.value || submitting.value) return;
	submitting.value = true;
	submitError.value = "";

	frappe.call({
		method: "cortex_rental.api.v1.quotes.create_quote_draft",
		type: "POST",
		args: {
			customer_id: customer.value.id,
			starts_at: fmtDateTime(new Date(startsAt.value)),
			ends_at: fmtDateTime(new Date(endsAt.value)),
			lines: JSON.stringify(
				lines.value.map((l) => ({
					item_id: l.item_id,
					quantity: l.quantity,
					unit_rate: l.unit_rate,
					discount_percentage: l.discount_percentage,
				})),
			),
			notes: notes.value || `Soumission créée via le Composer par ${frappe.session.user}.`,
		},
		callback(r) {
			submitting.value = false;
			const data = r.message && r.message.data;
			if (data && data.id) {
				frappe.set_route("Form", "Cortex Rental Transaction", data.id);
			}
		},
		error(r) {
			submitting.value = false;
			submitError.value =
				(r && r.responseJSON && (r.responseJSON.message || r.responseJSON.exc)) ||
				"Impossible de créer la soumission. Aucune transaction n'a été créée.";
		},
	});
}
</script>

<template>
	<div class="cortex-app cx-composer">
		<CortexPageHeader title="Nouvelle transaction" subtitle="Une soumission (quote) ne bloque pas l'inventaire.">
			<template #primary>
				<button class="cx-btn cx-btn-primary" :disabled="!canSubmit || submitting" @click="submit">
					{{ submitting ? "Création…" : "Créer la soumission" }}
				</button>
			</template>
		</CortexPageHeader>

		<div class="cx-composer-body">
			<main class="cx-composer-main">
				<!-- Client -->
				<section class="cx-surface cx-composer-section">
					<h3 class="cx-text-label">Client</h3>
					<div v-if="customer" class="cx-flex cx-items-center cx-gap-2">
						<span class="cx-badge cx-selected-customer">{{ customer.name }}</span>
						<button class="cx-btn" @click="clearCustomer">Changer</button>
					</div>
					<template v-else>
						<input
							v-model="customerSearch"
							class="cx-search-input"
							type="search"
							placeholder="Rechercher un client…"
							aria-label="Rechercher un client"
						/>
						<ul v-if="customerResults.length" class="cx-result-list">
							<li v-for="c in customerResults" :key="c.id">
								<button class="cx-result-item" @click="selectCustomer({ id: c.id, name: c.name })">
									<span>{{ c.name }}</span>
									<span class="cx-text-meta">{{ c.customer_group }} · {{ c.territory }}</span>
								</button>
							</li>
						</ul>
						<button class="cx-btn" style="margin-top: var(--space-2)" @click="showNewCustomerForm = !showNewCustomerForm">
							+ Nouveau client
						</button>
						<div v-if="showNewCustomerForm" class="cx-new-customer-form">
							<input v-model="newCustomer.customer_name" class="cx-search-input" placeholder="Nom du client" />
							<input v-model="newCustomer.email" class="cx-search-input" placeholder="Courriel (optionnel)" />
							<input v-model="newCustomer.phone" class="cx-search-input" placeholder="Téléphone (optionnel)" />
							<button
								class="cx-btn cx-btn-primary"
								:disabled="!newCustomer.customer_name.trim() || newCustomerSaving"
								@click="createCustomerDraft"
							>
								{{ newCustomerSaving ? "Création…" : "Créer le client" }}
							</button>
							<p v-if="newCustomerError" class="cx-text-critical">{{ newCustomerError }}</p>
						</div>
					</template>
				</section>

				<!-- Dates -->
				<section class="cx-surface cx-composer-section">
					<h3 class="cx-text-label">Dates</h3>
					<div class="cx-flex cx-gap-4">
						<label class="cx-flex-col cx-gap-1">
							<span class="cx-text-meta">Départ</span>
							<input v-model="startsAt" type="datetime-local" class="cx-search-input" />
						</label>
						<label class="cx-flex-col cx-gap-1">
							<span class="cx-text-meta">Retour</span>
							<input v-model="endsAt" type="datetime-local" class="cx-search-input" />
						</label>
					</div>
				</section>

				<!-- Équipements -->
				<section class="cx-surface cx-composer-section">
					<h3 class="cx-text-label">Équipements</h3>
					<input
						v-model="itemSearch"
						class="cx-search-input"
						type="search"
						placeholder="Rechercher un équipement, code ou catégorie…"
						aria-label="Rechercher un équipement"
					/>
					<ul v-if="itemResults.length" class="cx-result-list">
						<li v-for="item in itemResults" :key="item.item_code">
							<button class="cx-result-item" @click="addLine(item)">
								<span>{{ item.name }}</span>
								<span class="cx-text-meta">{{ item.category }} · {{ item.daily_rate }} $/jour</span>
							</button>
						</li>
					</ul>

					<CortexEmptyState v-if="!lines.length" message="Aucun équipement ajouté pour l'instant." />

					<table v-else class="cx-lines-table">
						<thead>
							<tr>
								<th>Équipement</th>
								<th>Qté</th>
								<th>Taux/jour</th>
								<th>Rabais %</th>
								<th>Disponibilité</th>
								<th>Montant</th>
								<th></th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(line, i) in lines" :key="line.item_id">
								<td>{{ line.name }}</td>
								<td><input v-model.number="line.quantity" type="number" min="1" class="cx-line-input" /></td>
								<td><input v-model.number="line.unit_rate" type="number" min="0" step="0.01" class="cx-line-input" /></td>
								<td>
									<input
										v-model.number="line.discount_percentage"
										type="number"
										min="0"
										max="100"
										class="cx-line-input"
									/>
								</td>
								<td>
									<span v-if="!line.availability" class="cx-text-meta">…</span>
									<CortexStatusBadge
										v-else-if="line.availability.is_available"
										state="quote"
										:label="`${line.availability.available_quantity} dispo.`"
									/>
									<CortexStatusBadge v-else state="conflict" :label="`${line.availability.available_quantity} dispo.`" />
								</td>
								<td class="cx-text-mono">
									{{ pricing && pricing.lines[i] ? pricing.lines[i].amount + " $" : "…" }}
								</td>
								<td><button class="cx-btn" aria-label="Retirer la ligne" @click="removeLine(i)">✕</button></td>
							</tr>
						</tbody>
					</table>
				</section>

				<!-- Notes -->
				<section class="cx-surface cx-composer-section">
					<h3 class="cx-text-label">Notes internes</h3>
					<textarea v-model="notes" class="cx-search-input" rows="3"></textarea>
				</section>
			</main>

			<!-- Résumé -->
			<aside class="cx-surface cx-composer-summary">
				<CortexStatusBadge state="quote" />
				<template v-if="pricingLoading">
					<p class="cx-text-meta">Calcul du prix…</p>
				</template>
				<template v-else-if="pricingError">
					<CortexErrorState :message="pricingError" @retry="refreshPricing" />
				</template>
				<template v-else-if="pricing">
					<dl class="cx-summary-list">
						<dt class="cx-text-label">Jours calendaires</dt>
						<dd class="cx-text-body">{{ pricing.calendar_days }}</dd>
						<dt class="cx-text-label">Jours facturables</dt>
						<dd class="cx-text-body">{{ pricing.billable_days }}</dd>
						<dt class="cx-text-label">Sous-total</dt>
						<dd class="cx-text-body">{{ pricing.subtotal }} $</dd>
						<dt class="cx-text-label">Total</dt>
						<dd class="cx-text-kpi">{{ pricing.total }} $</dd>
					</dl>
				</template>
				<p v-else class="cx-text-meta">Ajoutez un équipement pour voir le prix.</p>

				<p v-if="submitError" class="cx-text-critical" style="margin-top: var(--space-3)">{{ submitError }}</p>
			</aside>
		</div>
	</div>
</template>

<style scoped>
.cx-composer {
	padding: var(--space-4);
}
.cx-composer-body {
	display: flex;
	gap: var(--space-4);
	align-items: flex-start;
	flex-wrap: wrap;
}
.cx-composer-main {
	flex: 2;
	min-width: 420px;
	display: flex;
	flex-direction: column;
	gap: var(--space-4);
}
.cx-composer-summary {
	flex: 1;
	min-width: 260px;
	position: sticky;
	top: var(--space-4);
	padding: var(--space-4);
	display: flex;
	flex-direction: column;
	gap: var(--space-3);
}
.cx-composer-section {
	padding: var(--space-4);
}
.cx-composer-section h3 {
	margin: 0 0 var(--space-3);
}
.cx-search-input {
	width: 100%;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-2) var(--space-3);
	font-size: 13px;
	font-family: inherit;
	box-sizing: border-box;
}
.cx-result-list {
	list-style: none;
	margin: var(--space-2) 0 0;
	padding: 0;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	overflow: hidden;
}
.cx-result-item {
	width: 100%;
	display: flex;
	justify-content: space-between;
	gap: var(--space-2);
	padding: var(--space-2) var(--space-3);
	border: none;
	background: var(--cortex-surface);
	cursor: pointer;
	text-align: left;
	font-size: 13px;
}
.cx-result-item:hover {
	background: var(--cortex-surface-hover);
}
.cx-new-customer-form {
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
	margin-top: var(--space-3);
	padding-top: var(--space-3);
	border-top: 1px solid var(--cortex-border);
}
.cx-selected-customer {
	background: var(--cortex-primary-50);
	color: var(--cortex-primary-700);
	border-color: var(--cortex-primary-200);
}
.cx-lines-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 13px;
}
.cx-lines-table th {
	text-align: left;
	font-size: 11px;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--cortex-text-secondary);
	padding: var(--space-2);
	border-bottom: 1px solid var(--cortex-border);
}
.cx-lines-table td {
	padding: var(--space-2);
	border-bottom: 1px solid var(--cortex-surface-subtle);
	vertical-align: middle;
}
.cx-line-input {
	width: 64px;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-sm);
	padding: 3px 6px;
	font-size: 12.5px;
}
.cx-summary-list {
	margin: 0;
	display: grid;
	grid-template-columns: 1fr auto;
	row-gap: var(--space-2);
	align-items: center;
}
.cx-summary-list dd {
	margin: 0;
	text-align: right;
}
</style>
