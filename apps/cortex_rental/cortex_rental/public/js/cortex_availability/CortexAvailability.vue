<script setup>
import { ref, computed, onMounted } from "vue";

// Les données viennent du serveur (availability.get_matrix) : parc par article et réservations qui chevauchent la
// période. La grille déduit seulement « parc − quantités bloquantes du jour » à partir de ces lignes. Elle est
// indicative : la disponibilité réelle est revérifiée par le serveur au moment de réserver.
const BLOCKING = ["Reservation", "Contract", "Checked Out"];
const STATE_LABELS = {
	Quote: "Devis",
	Reservation: "Réservation",
	Contract: "Contrat",
	"Checked Out": "Sorti",
};
const SPANS = [
	{ days: 3, label: "3 jours" },
	{ days: 7, label: "7 jours" },
	{ days: 14, label: "14 jours" },
	{ days: 30, label: "30 jours" },
];

const start = ref(todayString());
const span = ref(window.innerWidth < 640 ? 3 : 14);
const search = ref("");
const category = ref("");
const items = ref([]);
const loading = ref(true);
const error = ref("");
const selected = ref(null);

function pad(n) {
	return String(n).padStart(2, "0");
}
function dateString(date) {
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
function todayString() {
	return dateString(new Date());
}
function addDays(ymd, n) {
	const [y, m, d] = ymd.split("-").map(Number);
	return dateString(new Date(y, m - 1, d + n));
}

const days = computed(() =>
	Array.from({ length: span.value }, (_, i) => {
		const ymd = addDays(start.value, i);
		const [y, m, d] = ymd.split("-").map(Number);
		const date = new Date(y, m - 1, d);
		return {
			ymd,
			weekday: date.toLocaleDateString("fr-CA", { weekday: "short" }).replace(".", ""),
			day: d,
			month: date.toLocaleDateString("fr-CA", { month: "short" }).replace(".", ""),
			weekend: date.getDay() === 0 || date.getDay() === 6,
			today: ymd === todayString(),
		};
	})
);
const periodLabel = computed(() => {
	const first = days.value[0];
	const last = days.value[days.value.length - 1];
	return `${first.day} ${first.month} au ${last.day} ${last.month}`;
});

const categories = computed(() => [...new Set(items.value.map((i) => i.category).filter(Boolean))].sort());

// Jour [ymd 00:00, ymd+1 00:00) : comparaison de chaînes « AAAA-MM-JJ hh:mm:ss » (même fuseau que le serveur).
function overlapping(item, ymd) {
	const dayStart = `${ymd} 00:00:00`;
	const dayEnd = `${addDays(ymd, 1)} 00:00:00`;
	return (item.blocks || []).filter((b) => b.starts_at < dayEnd && b.ends_at > dayStart);
}

function cell(item, ymd) {
	const blocks = overlapping(item, ymd);
	const blocking = blocks.filter((b) => BLOCKING.includes(b.rental_state));
	const booked = blocking.reduce((sum, b) => sum + Number(b.qty || 0), 0);
	const fleet = Number(item.fleet_quantity || 0);
	const free = fleet - booked;
	let status = "ok";
	if (fleet <= 0) status = "none";
	else if (free <= 0) status = "full";
	else if (booked > 0) status = "partial";
	return { blocks, free, booked, fleet, status, quotes: blocks.length - blocking.length };
}

const rows = computed(() => {
	const visible = items.value.filter((i) => !category.value || i.category === category.value);
	return visible.map((item) => ({ item, cells: days.value.map((d) => cell(item, d.ymd)) }));
});

const grouped = computed(() => {
	const map = new Map();
	rows.value.forEach((row) => {
		const key = row.item.category || "Sans catégorie";
		if (!map.has(key)) map.set(key, []);
		map.get(key).push(row);
	});
	return [...map.entries()];
});

const STATUS_TEXT = { ok: "libre", partial: "partiellement réservé", full: "complet", none: "aucun parc" };

function cellLabel(row, day, c) {
	return `${row.item.item_name}, ${day.weekday} ${day.day} ${day.month} : ${Math.max(c.free, 0)} sur ${c.fleet} disponible${c.free > 1 ? "s" : ""}, ${STATUS_TEXT[c.status]}`;
}

async function load() {
	loading.value = true;
	error.value = "";
	selected.value = null;
	try {
		const r = await frappe.call({
			method: "cortex_rental.api.v1.availability.get_matrix",
			type: "GET",
			args: { starts_at: `${start.value} 00:00:00`, ends_at: `${addDays(start.value, span.value)} 00:00:00`, search: search.value },
			silent: true,
		});
		items.value = ((r.message || {}).data || {}).items || [];
	} catch (e) {
		items.value = [];
		error.value = "La grille de disponibilité est indisponible pour le moment. Réessayez dans un instant.";
	} finally {
		loading.value = false;
	}
}

function shift(direction) {
	start.value = addDays(start.value, direction * span.value);
	load();
}
function today() {
	start.value = todayString();
	load();
}
function select(row, day, c) {
	selected.value = { row, day, cell: c };
}
function openRental(name) {
	frappe.set_route("Form", "Cortex Rental Transaction", name);
}
function newRental() {
	const s = selected.value;
	frappe.new_doc("Cortex Rental Transaction", {
		starts_at: `${s.day.ymd} 09:00:00`,
		ends_at: `${addDays(s.day.ymd, 1)} 09:00:00`,
	});
}

let timer = null;
function onSearch() {
	clearTimeout(timer);
	timer = setTimeout(load, 300);
}

onMounted(load);
defineExpose({ load });
</script>

<template>
	<section class="cx-avail" aria-labelledby="cx-avail-title">
		<header class="cx-avail-head">
			<div>
				<h1 id="cx-avail-title" class="cx-avail-title">Grille de disponibilité</h1>
				<p class="cx-avail-sub">
					Quantités libres par équipement et par jour. Indicatif : le serveur revérifie la disponibilité au moment de
					réserver.
				</p>
			</div>
			<div class="cx-avail-nav" role="group" aria-label="Période">
				<button type="button" class="cx-btn" aria-label="Période précédente" @click="shift(-1)">‹</button>
				<button type="button" class="cx-btn" @click="today">Aujourd'hui</button>
				<button type="button" class="cx-btn" aria-label="Période suivante" @click="shift(1)">›</button>
				<span class="cx-avail-period" aria-live="polite">{{ periodLabel }}</span>
			</div>
		</header>

		<div class="cx-avail-filters">
			<label class="cx-field">
				<span>Recherche</span>
				<input v-model="search" type="search" placeholder="Nom ou code de l'équipement" @input="onSearch" />
			</label>
			<label class="cx-field">
				<span>Catégorie</span>
				<select v-model="category">
					<option value="">Toutes</option>
					<option v-for="c in categories" :key="c" :value="c">{{ __(c) }}</option>
				</select>
			</label>
			<label class="cx-field">
				<span>Période affichée</span>
				<select v-model.number="span" @change="load">
					<option v-for="s in SPANS" :key="s.days" :value="s.days">{{ s.label }}</option>
				</select>
			</label>
		</div>

		<ul class="cx-avail-legend" aria-label="Légende">
			<li><span class="cx-dot cx-dot-ok"></span> Libre</li>
			<li><span class="cx-dot cx-dot-partial"></span> Partiellement réservé</li>
			<li><span class="cx-dot cx-dot-full"></span> Complet</li>
			<li><span class="cx-dot cx-dot-quote"></span> Devis en cours (ne bloque pas le matériel)</li>
		</ul>

		<p v-if="error" class="cx-avail-error" role="alert">{{ error }}</p>

		<div v-else-if="loading" class="cx-avail-skeleton" role="status" aria-label="Chargement de la grille">
			<span v-for="n in 6" :key="n"></span>
		</div>

		<p v-else-if="!rows.length" class="cx-avail-empty" role="status">
			Aucun équipement ne correspond. Ajoutez des profils d'équipement dans le Catalogue pour les voir ici.
		</p>

		<div v-else class="cx-avail-scroll" tabindex="0" role="region" aria-label="Grille de disponibilité, défilement horizontal">
			<table class="cx-avail-table">
				<thead>
					<tr>
						<th scope="col" class="cx-sticky">Équipement</th>
						<th
							v-for="d in days"
							:key="d.ymd"
							scope="col"
							:class="{ 'cx-weekend': d.weekend, 'cx-today': d.today }"
						>
							<span class="cx-wd">{{ d.weekday }}</span>
							<span class="cx-dn">{{ d.day }}</span>
						</th>
					</tr>
				</thead>
				<tbody v-for="[group, groupRows] in grouped" :key="group">
					<tr class="cx-group">
						<th :colspan="days.length + 1" scope="colgroup">{{ __(group) }}</th>
					</tr>
					<tr v-for="row in groupRows" :key="row.item.item_code">
						<th scope="row" class="cx-sticky">
							<span class="cx-name">{{ row.item.item_name }}</span>
							<span class="cx-code">{{ row.item.item_code }} · parc {{ row.item.fleet_quantity }}</span>
						</th>
						<td v-for="(c, i) in row.cells" :key="days[i].ymd" :class="{ 'cx-weekend': days[i].weekend }">
							<button
								type="button"
								class="cx-cell"
								:class="[`cx-cell-${c.status}`, { 'cx-cell-quote': c.quotes > 0 }]"
								:aria-label="cellLabel(row, days[i], c)"
								:aria-pressed="selected && selected.row === row && selected.day === days[i]"
								@click="select(row, days[i], c)"
							>
								{{ Math.max(c.free, 0) }}
							</button>
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<aside v-if="selected" class="cx-avail-detail" aria-live="polite">
			<div class="cx-avail-detail-head">
				<strong>{{ selected.row.item.item_name }}</strong>
				<span>{{ selected.day.weekday }} {{ selected.day.day }} {{ selected.day.month }}</span>
				<button type="button" class="cx-btn" aria-label="Fermer le détail" @click="selected = null">Fermer</button>
			</div>
			<p>
				{{ Math.max(selected.cell.free, 0) }} libre{{ selected.cell.free > 1 ? "s" : "" }} sur {{ selected.cell.fleet }} ·
				{{ selected.cell.booked }} bloqué{{ selected.cell.booked > 1 ? "s" : "" }}
			</p>
			<ul v-if="selected.cell.blocks.length" class="cx-avail-blocks">
				<li v-for="b in selected.cell.blocks" :key="b.transaction + b.starts_at">
					<a href="#" @click.prevent="openRental(b.transaction)">{{ b.transaction }}</a>
					— {{ STATE_LABELS[b.rental_state] || b.rental_state }}, {{ b.customer }}, {{ b.qty }} unité{{
						b.qty > 1 ? "s" : ""
					}}
					({{ b.starts_at.slice(0, 16) }} → {{ b.ends_at.slice(0, 16) }})
				</li>
			</ul>
			<p v-else class="cx-avail-muted">Aucune location sur cette journée.</p>
			<button type="button" class="cx-btn cx-btn-primary" @click="newRental">Nouvelle location ce jour-là</button>
		</aside>
	</section>
</template>

<style>
body[data-route="cortex-availability"] #page-cortex-availability .page-head {
	display: none;
}
.cx-avail {
	--ok: #047857;
	--ok-bg: #d1fae5;
	--partial: #92400e;
	--partial-bg: #fef3c7;
	--full: #991b1b;
	--full-bg: #fee2e2;
	--muted: #52525b;
	--line: #e4e4e7;
	padding: 16px 0 48px;
	color: #09090b;
}
.cx-avail-head {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
	gap: 12px;
	align-items: flex-end;
}
.cx-avail-title {
	margin: 0;
	font-size: 22px;
	font-weight: 650;
}
.cx-avail-sub,
.cx-avail-muted {
	margin: 4px 0 0;
	color: var(--muted);
	font-size: 13px;
	max-width: 60ch;
}
.cx-avail-nav {
	display: flex;
	align-items: center;
	gap: 6px;
	flex-wrap: wrap;
}
.cx-avail-period {
	margin-left: 8px;
	font-weight: 600;
	font-size: 14px;
}
.cx-btn {
	min-height: 34px;
	padding: 0 12px;
	border: 1px solid var(--line);
	border-radius: 8px;
	background: #fff;
	color: #09090b;
	font: inherit;
	font-size: 13px;
	cursor: pointer;
	transition: border-color 0.15s, background 0.15s;
}
.cx-btn:hover {
	border-color: var(--ok);
	background: #ecfdf5;
}
.cx-btn-primary {
	background: var(--ok);
	border-color: var(--ok);
	color: #fff;
}
.cx-btn-primary:hover {
	background: #065f34;
	color: #fff;
}
.cx-avail-filters {
	display: flex;
	flex-wrap: wrap;
	gap: 12px;
	margin: 16px 0 8px;
}
.cx-field {
	display: flex;
	flex-direction: column;
	gap: 4px;
	font-size: 12px;
	color: var(--muted);
	min-width: min(200px, 100%);
}
.cx-field input,
.cx-field select {
	height: 34px;
	padding: 0 10px;
	border: 1px solid var(--line);
	border-radius: 8px;
	background: #fff;
	color: #09090b;
	font: inherit;
	font-size: 13px;
}
.cx-avail-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 16px;
	list-style: none;
	margin: 8px 0 12px;
	padding: 0;
	font-size: 12px;
	color: var(--muted);
}
.cx-dot {
	display: inline-block;
	width: 10px;
	height: 10px;
	border-radius: 3px;
	margin-right: 4px;
	vertical-align: -1px;
}
.cx-dot-ok { background: var(--ok-bg); border: 1px solid var(--ok); }
.cx-dot-partial { background: var(--partial-bg); border: 1px solid var(--partial); }
.cx-dot-full { background: var(--full-bg); border: 1px solid var(--full); }
.cx-dot-quote { border: 1px dashed var(--muted); }
.cx-avail-scroll {
	overflow-x: auto;
	border: 1px solid var(--line);
	border-radius: 12px;
	background: #fff;
	animation: cx-fade 220ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
.cx-avail-table {
	border-collapse: separate;
	border-spacing: 0;
	width: 100%;
	font-size: 13px;
}
.cx-avail-table th,
.cx-avail-table td {
	padding: 4px;
	border-bottom: 1px solid var(--line);
	text-align: center;
	font-weight: 500;
}
.cx-avail-table thead th {
	background: #f4f4f5;
	color: var(--muted);
	font-size: 12px;
	white-space: nowrap;
}
.cx-avail-table .cx-today {
	background: #d1fae5;
	color: #064e3b;
}
.cx-avail-table .cx-weekend:not(.cx-today) {
	background: #fafafa;
}
.cx-wd {
	display: block;
	text-transform: capitalize;
}
.cx-dn {
	display: block;
	font-size: 14px;
	font-weight: 650;
	color: #09090b;
}
.cx-sticky {
	position: sticky;
	left: 0;
	z-index: 1;
	min-width: 180px;
	max-width: 220px;
	text-align: left !important;
	background: #fff;
	border-right: 1px solid var(--line);
}
thead .cx-sticky {
	background: #f4f4f5;
}
.cx-name {
	display: block;
	font-weight: 600;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cx-code {
	display: block;
	font-size: 11px;
	color: var(--muted);
}
.cx-group th {
	background: #f4f4f5;
	text-align: left;
	font-size: 11px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--muted);
	padding: 6px 12px;
}
.cx-cell {
	width: 100%;
	min-width: 40px;
	height: 36px;
	border-radius: 8px;
	border: 1px solid transparent;
	font: inherit;
	font-weight: 650;
	cursor: pointer;
	transition: transform 0.12s, box-shadow 0.12s;
}
.cx-cell:hover {
	transform: translateY(-1px);
	box-shadow: 0 2px 8px rgba(9, 9, 11, 0.12);
}
.cx-cell:focus-visible,
.cx-avail-scroll:focus-visible {
	outline: 2px solid var(--ok);
	outline-offset: 2px;
}
.cx-cell-ok { background: var(--ok-bg); color: var(--ok); }
.cx-cell-partial { background: var(--partial-bg); color: var(--partial); }
.cx-cell-full { background: var(--full-bg); color: var(--full); }
.cx-cell-none { background: #f4f4f5; color: var(--muted); }
.cx-cell-quote { border: 1px dashed var(--muted); }
.cx-cell[aria-pressed="true"] { box-shadow: 0 0 0 2px #09090b; }
.cx-avail-detail {
	margin-top: 16px;
	padding: 14px 16px;
	border: 1px solid var(--line);
	border-radius: 12px;
	background: #fff;
	animation: cx-rise 220ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
.cx-avail-detail-head {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 10px;
}
.cx-avail-detail-head .cx-btn {
	margin-left: auto;
}
.cx-avail-blocks {
	margin: 8px 0 12px;
	padding-left: 18px;
	font-size: 13px;
}
.cx-avail-blocks a {
	font-weight: 600;
}
.cx-avail-error {
	padding: 12px 14px;
	border: 1px solid #fecaca;
	border-radius: 10px;
	background: #fef2f2;
	color: var(--full);
}
.cx-avail-empty {
	padding: 24px;
	text-align: center;
	color: var(--muted);
}
.cx-avail-skeleton span {
	display: block;
	height: 38px;
	margin-bottom: 8px;
	border-radius: 8px;
	background: linear-gradient(90deg, #f4f4f5 25%, #e9e9ec 37%, #f4f4f5 63%);
	background-size: 400% 100%;
	animation: cx-shimmer 1.4s linear infinite;
}
@media (max-width: 640px) {
	.cx-sticky {
		min-width: 130px;
	}
	.cx-avail-period {
		margin-left: 0;
		width: 100%;
	}
}
</style>
