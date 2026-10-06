<script setup>
// Questionnaire « Disponibilité » : période (7 j, 30 j ou dates) + catégorie → mini-grille calculée par le serveur.
// Chaque ligne peut démarrer un devis avec ce matériel. L'état « libre » vient du serveur, jamais de l'assistant.
import { ref, computed, onMounted } from "vue";
import CopilotFlowShell from "./CopilotFlowShell.vue";
import { apiCall } from "./chatClient.js";

const emit = defineEmits(["quote"]);

const STEPS = ["Période", "Résultat"];
const STATUS = { ok: "Libre", partial: "Partiellement pris", full: "Complet", none: "Aucun au parc" };

const step = ref(1);
const error = ref("");
const busy = ref(false);

function iso(date) {
	const pad = (n) => String(n).padStart(2, "0");
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
function plusDays(base, days) {
	const d = new Date(base);
	d.setDate(d.getDate() + days);
	return d;
}

const today = iso(new Date());
const preset = ref("7"); // « 7 », « 30 » ou « dates »
const from = ref(today);
const to = ref(iso(plusDays(new Date(), 6)));
const category = ref("");
const categories = ref([]);
const rows = ref([]);
const asked = ref({ from: "", to: "", category: "" });

const days = computed(() => {
	if (preset.value === "7") return { from: today, to: iso(plusDays(new Date(), 6)) };
	if (preset.value === "30") return { from: today, to: iso(plusDays(new Date(), 29)) };
	return { from: from.value, to: to.value };
});
const periodError = computed(() => {
	if (preset.value !== "dates") return "";
	if (!from.value || !to.value) return "Indiquez la première et la dernière journée.";
	if (to.value < from.value) return "La dernière journée doit venir après la première.";
	return "";
});

const grouped = computed(() => {
	const map = {};
	for (const row of rows.value) (map[row.category || "Autre"] = map[row.category || "Autre"] || []).push(row);
	return Object.entries(map).sort(([a], [b]) => a.localeCompare(b, "fr"));
});

const label = (value) => {
	const [y, m, d] = value.split("-").map(Number);
	return new Date(y, m - 1, d).toLocaleDateString("fr-CA", { day: "numeric", month: "short", year: "numeric" });
};

async function query(start, end, cat) {
	const data = await apiCall("cortex_rental.api.v1.availability.get_period_summary", { starts_at: start, ends_at: end, category: cat || "" });
	return data.items || [];
}

onMounted(async () => {
	try {
		// Les catégories proposées sont celles du parc réel.
		const all = await query(today, today, "");
		categories.value = [...new Set(all.map((r) => r.category).filter(Boolean))].sort((a, b) => a.localeCompare(b, "fr"));
	} catch (e) {
		error.value = e.message;
	}
});

async function show() {
	error.value = "";
	if (periodError.value) return (error.value = periodError.value);
	busy.value = true;
	try {
		const { from: start, to: end } = days.value;
		rows.value = await query(start, end, category.value);
		asked.value = { from: start, to: end, category: category.value };
		step.value = 2;
	} catch (e) {
		error.value = e.message;
	} finally {
		busy.value = false;
	}
}

function quoteWith(codes) {
	emit("quote", { preselect: codes, starts: `${asked.value.from}T09:00`, ends: `${asked.value.to}T17:00` });
}

function openGrid() {
	frappe.set_route("cortex-availability");
}
</script>

<template>
	<CopilotFlowShell
		title="Disponibilité du parc"
		subtitle="Ce qui reste libre sur la période, calculé par le serveur à partir des réservations, contrats et retenues."
		:steps="STEPS"
		:step="step"
		:error="error"
	>
		<div v-if="step === 1" class="a-step">
			<span class="a-label" id="a-period">Quelle période ?</span>
			<div class="a-seg" role="radiogroup" aria-labelledby="a-period">
				<button type="button" role="radio" :aria-checked="preset === '7'" :class="{ on: preset === '7' }" @click="preset = '7'">7 prochains jours</button>
				<button type="button" role="radio" :aria-checked="preset === '30'" :class="{ on: preset === '30' }" @click="preset = '30'">30 prochains jours</button>
				<button type="button" role="radio" :aria-checked="preset === 'dates'" :class="{ on: preset === 'dates' }" @click="preset = 'dates'">Dates précises</button>
			</div>
			<div v-if="preset === 'dates'" class="a-dates">
				<label class="a-field"><span class="a-label">Du</span><input v-model="from" class="a-input" type="date" /></label>
				<label class="a-field"><span class="a-label">Au</span><input v-model="to" class="a-input" type="date" /></label>
			</div>
			<p v-else class="a-hint">Du {{ label(days.from) }} au {{ label(days.to) }}.</p>

			<label class="a-field">
				<span class="a-label">Catégorie</span>
				<select v-model="category" class="a-input">
					<option value="">Toutes les catégories</option>
					<option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
				</select>
			</label>
		</div>

		<div v-else class="a-step">
			<p class="a-who">
				Du <strong>{{ label(asked.from) }}</strong> au <strong>{{ label(asked.to) }}</strong>
				<span v-if="asked.category"> · {{ asked.category }}</span>
				<span class="a-hint"> · « libre » = disponible chaque jour de la période.</span>
			</p>
			<div class="a-grid" role="group" aria-label="Disponibilité par équipement">
				<template v-for="[cat, items] in grouped" :key="cat">
					<h4 class="a-cat">{{ cat }}</h4>
					<div v-for="row in items" :key="row.item_code" class="a-row">
						<div class="a-main">
							<strong>{{ row.item_name }}</strong>
							<span class="a-meta">{{ row.item_code }}</span>
						</div>
						<span class="a-badge" :class="row.status">{{ STATUS[row.status] }}</span>
						<span class="a-count" :title="`Parc : ${row.fleet} · réservé au pic : ${row.booked} · retenu par des devis : ${row.held}`">
							<strong>{{ row.free }}</strong> libre{{ row.free > 1 ? "s" : "" }} sur {{ row.fleet }}
						</span>
						<button type="button" class="a-act" :disabled="row.free <= 0" @click="quoteWith([row.item_code])">Créer un devis avec ceci</button>
					</div>
				</template>
				<p v-if="!rows.length" class="a-empty">Aucun équipement ne correspond à cette catégorie.</p>
			</div>
		</div>

		<template #footer>
			<template v-if="step === 1">
				<button type="button" class="cx-btn cx-btn-primary a-next" :disabled="busy" @click="show">{{ busy ? "Un instant…" : "Voir la disponibilité" }}</button>
			</template>
			<template v-else>
				<button type="button" class="cx-btn cx-btn-secondary" @click="step = 1">Modifier la période</button>
				<button type="button" class="cx-btn cx-btn-secondary" @click="openGrid">Ouvrir la grille complète</button>
				<button type="button" class="cx-btn cx-btn-primary a-next" @click="quoteWith([])">Créer un devis pour cette période</button>
			</template>
		</template>
	</CopilotFlowShell>
</template>

<style scoped>
.a-step {
	display: grid;
	gap: 12px;
}
.a-label {
	font-size: 12.5px;
	font-weight: 600;
	color: #55544f;
}
.a-hint {
	margin: 0;
	font-size: 12.5px;
	color: #6b6a66;
	font-weight: 400;
}
.a-seg {
	display: inline-flex;
	flex-wrap: wrap;
	gap: 6px;
}
.a-seg button {
	height: 36px;
	padding: 0 14px;
	border: 1px solid #e0dfda;
	border-radius: 999px;
	background: #fff;
	font-size: 13.5px;
	cursor: pointer;
	transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.a-seg button:hover {
	background: #f7f7f5;
}
.a-seg button.on {
	border-color: #047857;
	background: #f1faf5;
	color: #066336;
	font-weight: 600;
}
.a-dates {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}
.a-field {
	display: grid;
	gap: 5px;
}
.a-input {
	width: 100%;
	height: 38px;
	padding: 0 10px;
	border: 1px solid #e0dfda;
	border-radius: 9px;
	background: #fff;
	font-size: 14px;
}
.a-input:focus {
	border-color: #047857;
	box-shadow: 0 0 0 3px rgba(4, 120, 87, 0.12);
	outline: none;
}
.a-who {
	margin: 0;
	font-size: 13.5px;
	color: #3a3a37;
}
.a-grid {
	display: grid;
	gap: 6px;
	max-height: 380px;
	overflow-y: auto;
}
.a-cat {
	margin: 8px 0 0;
	font-size: 11.5px;
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: #6b6a66;
}
.a-row {
	display: grid;
	grid-template-columns: minmax(0, 1.4fr) auto auto auto;
	align-items: center;
	gap: 6px 12px;
	padding: 9px 12px;
	border: 1px solid #efeeea;
	border-radius: 10px;
}
.a-main {
	display: grid;
	min-width: 0;
}
.a-main strong {
	font-size: 13.5px;
	font-weight: 600;
}
.a-meta {
	font-size: 12px;
	color: #6b6a66;
}
.a-badge {
	padding: 2px 9px;
	border-radius: 999px;
	background: #e7f6ee;
	color: #066336;
	font-size: 11.5px;
	font-weight: 600;
	white-space: nowrap;
}
.a-badge.partial {
	background: #fdf1de;
	color: #8a4b00;
}
.a-badge.full,
.a-badge.none {
	background: #fbeaea;
	color: #b42318;
}
.a-count {
	font-size: 12.5px;
	color: #55544f;
	white-space: nowrap;
	font-variant-numeric: tabular-nums;
}
.a-act {
	height: 30px;
	padding: 0 11px;
	border: 1px solid #e0dfda;
	border-radius: 8px;
	background: #fff;
	font-size: 12.5px;
	font-weight: 600;
	color: #066336;
	cursor: pointer;
	transition: background-color 0.15s ease;
}
.a-act:hover:not(:disabled) {
	background: #f1faf5;
}
.a-act:disabled {
	color: #a3a29d;
	cursor: not-allowed;
}
.a-empty {
	font-size: 13px;
	color: #6b6a66;
}
.a-next {
	margin-left: auto;
}
@media (max-width: 640px) {
	.a-dates {
		grid-template-columns: minmax(0, 1fr);
	}
	.a-row {
		grid-template-columns: auto minmax(0, 1fr);
	}
	.a-main {
		grid-column: 1 / -1;
	}
	.a-act {
		grid-column: 1 / -1;
		justify-self: start;
	}
}
</style>
