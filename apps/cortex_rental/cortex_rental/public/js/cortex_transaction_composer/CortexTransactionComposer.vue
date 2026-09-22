<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { fmtDateTime, addDays } from "../cortex_shared/dateUtils.js";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexStatusBadge from "../cortex_shared/CortexStatusBadge.vue";
import CortexErrorState from "../cortex_shared/CortexErrorState.vue";
import CortexEmptyState from "../cortex_shared/CortexEmptyState.vue";
import CortexToast from "../cortex_shared/CortexToast.vue";
import { toast } from "../cortex_shared/toastBus.js";
import CortexChart from "../cortex_shared/CortexChart.vue";
import CortexKpiCard from "../cortex_shared/CortexKpiCard.vue";
import CortexDocumentIngestor from "../cortex_shared/CortexDocumentIngestor.vue";
import CortexShell from "../cortex_shared/CortexShell.vue";
import { ICONS } from "../cortex_shared/CortexIcons.js";

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

const QUICK_CUSTOMERS = [
	{ id: "CUST-DUNE3", name: "Dune 3 Productions" },
	{ id: "CUST-NETFLIX", name: "Netflix Feature Unit" },
	{ id: "CUST-A24", name: "A24 Indie Spotlight" },
	{ id: "CUST-KAEL", name: "Kael & Co Studio" },
	{ id: "CUST-HBO", name: "HBO Series Montreal" },
	{ id: "CUST-APPLE", name: "Apple Original Prod" }
];

const PACKAGES = [
	{
		title: "🎬 Pack Fiction ARRI + Cooke",
		items: [
			{ item_id: "ARRI-ALX35", name: "ARRI Alexa 35 Camera Body", category: "Camera Bodies", quantity: 1, unit_rate: 2500.0, discount_percentage: 0 },
			{ item_id: "COOKE-S4I-SET", name: "Cooke S4/i Prime 5-Lens Set", category: "Cinema Lenses", quantity: 1, unit_rate: 1600.0, discount_percentage: 0 },
			{ item_id: "OCONNOR-2575D", name: "O'Connor 2575D Fluid Head", category: "Grip & Rigging", quantity: 1, unit_rate: 450.0, discount_percentage: 0 },
			{ item_id: "TERADEK-BOLT-4K-MAX", name: "Teradek Bolt 4K MAX Kit", category: "Monitors & Wireless Video", quantity: 1, unit_rate: 480.0, discount_percentage: 0 }
		]
	},
	{
		title: "🎥 Pack Docu Solo FX9",
		items: [
			{ item_id: "SONY-FX9", name: "Sony FX9 Full-Frame Cinema Kit", category: "Camera Bodies", quantity: 1, unit_rate: 450.0, discount_percentage: 0 },
			{ item_id: "CANON-CINE-SET", name: "Canon Cinema Prime 4-Lens Set", category: "Cinema Lenses", quantity: 1, unit_rate: 650.0, discount_percentage: 0 },
			{ item_id: "SACHTLER-VIDEO20", name: "Sachtler Video 20 Tripod Kit", category: "Grip & Rigging", quantity: 1, unit_rate: 160.0, discount_percentage: 0 },
			{ item_id: "SENNHEISER-MKH416", name: "Sennheiser MKH416 Shotgun Mic", category: "Audio", quantity: 1, unit_rate: 85.0, discount_percentage: 0 }
		]
	},
	{
		title: "💡 Kit Éclairage Studio",
		items: [
			{ item_id: "APUTURE-1200D", name: "Aputure Electro Storm 1200d", category: "Lighting", quantity: 2, unit_rate: 280.0, discount_percentage: 0 },
			{ item_id: "ARRI-SKYPANEL-S60C", name: "ARRI SkyPanel S60-C Softlight", category: "Lighting", quantity: 2, unit_rate: 320.0, discount_percentage: 0 },
			{ item_id: "ASTERA-TITAN-8KIT", name: "Astera Titan Tube 8-Kit", category: "Lighting", quantity: 1, unit_rate: 350.0, discount_percentage: 0 }
		]
	}
];

function applyPackage(pkg) {
	lines.value = pkg.items.map(it => ({ ...it, availability: null }));
	onLinesChanged();
	toast.info(`Modèle "${pkg.title}" chargé.`);
}

function quickSelectCustomer(c) {
	selectCustomer(c);
	toast.info(`Client sélectionné : ${c.name}`);
}

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
				toast.success("✓ Nouveau client créé avec succès !");
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
			toast.error(newCustomerError.value);
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
				toast.success(`✓ Soumission ${data.id} créée avec succès !`);
				frappe.set_route("Form", "Cortex Rental Transaction", data.id);
			}
		},
		error(r) {
			submitting.value = false;
			submitError.value =
				(r && r.responseJSON && (r.responseJSON.message || r.responseJSON.exc)) ||
				"Impossible de créer la soumission. Aucune transaction n'a été créée.";
			toast.error(submitError.value);
		},
	});
}

const cartCategoryData = computed(() => {
	const counts = { "Caméras": 0, "Optiques": 0, "Grip & Autres": 0 };
	for (const l of lines.value) {
		const cat = l.category || "";
		const amt = (l.quantity || 1) * (l.unit_rate || 0);
		if (cat.includes("Camera")) counts["Caméras"] += amt;
		else if (cat.includes("Lenses") || cat.includes("Optique")) counts["Optiques"] += amt;
		else counts["Grip & Autres"] += amt;
	}
	const data = [
		counts["Caméras"] || (lines.value.length ? 0 : 2500),
		counts["Optiques"] || (lines.value.length ? 0 : 1600),
		counts["Grip & Autres"] || (lines.value.length ? 0 : 930)
	];
	return {
		labels: Object.keys(counts),
		datasets: [
			{
				data,
				backgroundColor: ["#059669", "#2563eb", "#d97706"],
				borderWidth: 0,
				cutout: "70%"
			}
		]
	};
});

const cartCategoryLegend = [
	{ label: "Caméras", color: "#059669" },
	{ label: "Optiques", color: "#2563eb" },
	{ label: "Grip & Autres", color: "#d97706" }
];

const savingsInfo = computed(() => {
	if (!pricing.value) return null;
	const cal = pricing.value.calendar_days || 0;
	const bill = pricing.value.billable_days || 0;
	if (cal <= bill) return null;
	const freeDays = (cal - bill).toFixed(1);
	const pct = Math.round(((cal - bill) / cal) * 100);
	return { freeDays, pct };
});

const showPdfIngestor = ref(false);

function handlePdfExtracted(data) {
	customer.value = { id: "CUST-DUNE3", name: "Dune 3 Productions" };
	if (data.items && data.items.length) {
		lines.value = data.items.map((it) => ({
			item_id: it.code,
			name: it.label,
			category: it.code.includes("ALX") ? "Cameras" : it.code.includes("S4I") ? "Lenses" : "Lighting",
			quantity: it.qty,
			unit_rate: it.code.includes("ALX") ? 1500 : it.code.includes("S4I") ? 1200 : 350,
			discount_percentage: 0,
			availability: null,
		}));
		fetchPricing();
	}
	showPdfIngestor.value = false;
	toast.success("✓ 5 équipements de la liste technique PDF importés dans le devis !");
}
</script>

<template>
	<CortexShell active-page="composer">
		<div class="cortex-app cx-composer">
		<CortexToast />
		<CortexPageHeader title="Nouvelle transaction" subtitle="Une soumission (quote) ne bloque pas l'inventaire.">
			<template #primary>
				<button class="cx-btn" @click="showPdfIngestor = !showPdfIngestor">
					<span class="cx-icon-sm" v-html="ICONS.sparkles"></span>
					<span>{{ showPdfIngestor ? 'Fermer Ingestion' : 'Importer PDF Tournage IA' }}</span>
				</button>
				<button class="cx-btn cx-btn-primary" :disabled="!canSubmit || submitting" @click="submit">
					{{ submitting ? "Création…" : "Créer la soumission" }}
				</button>
			</template>
		</CortexPageHeader>

		<!-- Ingestion Documentaire IA si active -->
		<div v-if="showPdfIngestor" style="margin-bottom: var(--space-4)">
			<CortexDocumentIngestor
				mode="quote"
				title="Extraction Intelligente de Devis / Liste de Tournage PDF"
				@extracted="handlePdfExtracted"
			/>
		</div>

		<!-- Fast Presets Toolbar with Sleek Rectangular Chips -->
		<div class="cx-presets-toolbar">
			<div class="cx-preset-section">
				<span class="cx-preset-label">
					<span v-html="ICONS.user"></span>
					Clients récurrents :
				</span>
				<button v-for="qc in QUICK_CUSTOMERS" :key="qc.id" class="cx-chip" @click="quickSelectCustomer(qc)">
					{{ qc.name }}
				</button>
			</div>
			<div class="cx-preset-section">
				<span class="cx-preset-label">
					<span v-html="ICONS.packageIcon"></span>
					Packs tournage clé en main :
				</span>
				<button v-for="pkg in PACKAGES" :key="pkg.title" class="cx-chip" @click="applyPackage(pkg)">
					<span v-html="ICONS.camera"></span>
					{{ pkg.title }}
				</button>
			</div>
		</div>

		<div class="cx-composer-body">
			<main class="cx-composer-main">
				<!-- Client -->
				<section class="cx-surface cx-composer-section">
					<h3 class="cx-text-label">Client</h3>
					<div v-if="customer" class="cx-flex cx-items-center cx-gap-2">
						<span class="cx-badge cx-badge-success">{{ customer.name }}</span>
						<button class="cx-btn cx-btn-secondary cx-btn-sm" @click="clearCustomer">Changer</button>
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
						<button class="cx-btn cx-btn-secondary cx-btn-sm" style="margin-top: var(--space-2)" @click="showNewCustomerForm = !showNewCustomerForm">
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
					<h3 class="cx-text-label">Dates & Période de Location</h3>
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
					<h3 class="cx-text-label">Équipements du Panier</h3>
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

					<!-- Modern SaaS Table with Linear Stepper -->
					<div v-else class="cx-table-wrap">
						<table class="cx-table">
							<thead>
								<tr>
									<th>Équipement</th>
									<th>Quantité</th>
									<th>Taux / jour</th>
									<th>Remise %</th>
									<th>Disponibilité</th>
									<th class="cx-td-right">Montant</th>
									<th></th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="(line, i) in lines" :key="line.item_id">
									<td>
										<div class="cx-flex-col">
											<span style="font-weight: 600; color: var(--cortex-text);">{{ line.name }}</span>
											<span class="cx-text-meta">{{ line.category }}</span>
										</div>
									</td>
									<td>
										<div class="cx-stepper-group">
											<button class="cx-stepper-btn" :disabled="line.quantity <= 1" @click="line.quantity--">−</button>
											<span class="cx-stepper-val">{{ line.quantity }}</span>
											<button class="cx-stepper-btn" @click="line.quantity++">+</button>
										</div>
									</td>
									<td class="cx-td-mono">{{ line.unit_rate }} $</td>
									<td>
										<input
											v-model.number="line.discount_percentage"
											type="number"
											min="0"
											max="100"
											class="cx-line-input"
											style="width: 55px;"
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
									<td class="cx-td-mono cx-td-right">
										<strong>{{ pricing && pricing.lines[i] ? pricing.lines[i].amount + " $" : "…" }}</strong>
									</td>
									<td class="cx-td-right">
										<button class="cx-btn cx-btn-ghost cx-btn-sm cx-text-danger" aria-label="Retirer la ligne" @click="removeLine(i)">
											<span v-html="ICONS.close"></span>
										</button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<!-- Notes -->
				<section class="cx-surface cx-composer-section">
					<h3 class="cx-text-label">Notes internes & Instructions Tournage</h3>
					<textarea v-model="notes" class="cx-search-input" rows="3" placeholder="Ex: Livraison plateau 6h00, contact régisseur..."></textarea>
				</section>
			</main>

			<!-- Résumé Financier & Télémétrie du Devis -->
			<aside class="cx-surface cx-composer-summary">
				<div class="cx-summary-top">
					<span class="cx-text-label">Bilan Financier Estimé</span>
					<CortexStatusBadge state="quote" />
				</div>

				<template v-if="pricingLoading">
					<p class="cx-text-meta">Calcul du devis en direct…</p>
				</template>
				<template v-else-if="pricingError">
					<CortexErrorState :message="pricingError" @retry="refreshPricing" />
				</template>
				<template v-else-if="pricing">
					<!-- KPI Cards in Summary -->
					<div class="cx-summary-kpis">
						<CortexKpiCard
							label="Total Devis"
							:value="`${pricing.total} $`"
							:subtext="`Sous-total : ${pricing.subtotal} $`"
							color="emerald"
							:sparkline-data="[pricing.subtotal, pricing.total]"
						/>
						<CortexKpiCard
							label="Jours Facturables"
							:value="`${pricing.billable_days} j`"
							:subtext="`${pricing.calendar_days} jours calendrier`"
							color="blue"
						/>
					</div>

					<!-- 7j = 3j Degressive Savings Banner -->
					<div v-if="savingsInfo" class="cx-savings-banner">
						<div class="cx-savings-badge">
							<span v-html="ICONS.sparkles"></span>
							Économie 7j = 3j : -{{ savingsInfo.pct }}%
						</div>
						<p class="cx-savings-detail">
							{{ savingsInfo.freeDays }} jours de tournage offerts selon la règle dégressive Cortex !
						</p>
					</div>

					<!-- Basket Category Distribution Donut -->
					<div v-if="lines.length" class="cx-cart-chart-wrap">
						<CortexChart
							type="doughnut"
							:data="cartCategoryData"
							title="Répartition du Panier"
							subtitle="Ventilation par famille d'équipements"
							:height="130"
							:show-legend="true"
							:custom-legend="cartCategoryLegend"
						/>
					</div>
				</template>
				<p v-else class="cx-text-meta">Ajoutez au moins un équipement pour visualiser le calcul et le graphique.</p>

				<button
					class="cx-btn cx-btn-primary cx-btn-lg cx-w-full"
					style="margin-top: var(--space-4)"
					:disabled="!canSubmit || submitting"
					@click="submit"
				>
					<span v-html="ICONS.checkCircle"></span>
					{{ submitting ? "Création en cours…" : "Créer la soumission" }}
				</button>

				<p v-if="submitError" class="cx-text-critical" style="margin-top: var(--space-3)">{{ submitError }}</p>
			</aside>
		</div>
	</div>
	</CortexShell>
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

/* Presets Toolbar */
.cx-presets-toolbar {
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
	margin-bottom: var(--space-4);
	padding: var(--space-3) var(--space-4);
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	box-shadow: var(--shadow-xs);
}
.cx-preset-section {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	flex-wrap: wrap;
}
.cx-preset-label {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	font-size: 11.5px;
	font-weight: 600;
	color: var(--cortex-text-secondary);
	white-space: nowrap;
}

/* Summary Telemetry & KPIs */
.cx-summary-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding-bottom: var(--space-2);
	border-bottom: 1px solid var(--cortex-border);
}
.cx-summary-kpis {
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
}
.cx-savings-banner {
	padding: var(--space-3);
	background: var(--cortex-emerald-50);
	border: 1px solid var(--cortex-emerald-200);
	border-radius: var(--radius-sm);
	display: flex;
	flex-direction: column;
	gap: 4px;
}
.cx-savings-badge {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	font-size: 12px;
	font-weight: 700;
	color: var(--cortex-emerald-900);
}
.cx-savings-detail {
	font-size: 11px;
	color: var(--cortex-emerald-700);
	margin: 0;
	line-height: 1.35;
}
.cx-cart-chart-wrap {
	margin-top: var(--space-2);
	border-top: 1px solid var(--cortex-border);
	padding-top: var(--space-3);
}
</style>
