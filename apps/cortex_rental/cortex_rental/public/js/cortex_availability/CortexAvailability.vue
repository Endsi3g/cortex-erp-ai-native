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

// Une catégorie par sous-page (/app/cortex-availability/<catégorie>) : la liste vient de la barre de navigation.
const CATEGORY_ORDER = (window.cortex && window.cortex.CATEGORIES) || [];

// Jour [ymd 00:00, ymd+1 00:00) : comparaison de chaînes « AAAA-MM-JJ hh:mm:ss » (même fuseau que le serveur).
function overlapping(item, ymd) {
	const dayStart = `${ymd} 00:00:00`;
	const dayEnd = `${addDays(ymd, 1)} 00:00:00`;
	return (item.blocks || []).filter((b) => b.starts_at < dayEnd && b.ends_at > dayStart);
}

// Un devis retient du matériel tant que sa retenue est valide (calculée par le serveur : hold_until).
function holding(b) {
	return b.rental_state === "Quote" && b.hold_until && b.hold_until > nowString();
}
function nowString() {
	const d = new Date();
	return `${dateString(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
}

function cell(item, ymd) {
	const blocks = overlapping(item, ymd);
	const blocking = blocks.filter((b) => BLOCKING.includes(b.rental_state));
	const held = blocks.filter(holding).reduce((sum, b) => sum + Number(b.qty || 0), 0);
	const booked = blocking.reduce((sum, b) => sum + Number(b.qty || 0), 0);
	const fleet = Number(item.fleet_quantity || 0);
	const free = fleet - booked - held;
	let status = "ok";
	if (fleet <= 0) status = "none";
	else if (free <= 0) status = "full";
	else if (booked + held > 0) status = "partial";
	return { blocks, free, booked, held, fleet, status, quotes: 0 };
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

// Part du parc déjà bloquée (0 à 100) : sert au remplissage discret de la cellule.
function fillPct(c) {
	if (c.fleet <= 0) return 0;
	return Math.max(0, Math.min(100, Math.round((c.booked / c.fleet) * 100)));
}
function holdPct(c) {
	if (c.fleet <= 0) return 0;
	return Math.max(0, Math.min(100, Math.round(((c.booked + c.held) / c.fleet) * 100)));
}

// Locations et retenues de la période affichée (une ligne par dossier), pour remplir la page de choses utiles.
const timeline = computed(() => {
	const map = new Map();
	rows.value.forEach((row) =>
		(row.item.blocks || []).forEach((b) => {
			const entry = map.get(b.transaction) || { ...b, items: [], qty: 0 };
			entry.items.push(row.item.item_name);
			entry.qty += Number(b.qty || 0);
			map.set(b.transaction, entry);
		})
	);
	return [...map.values()]
		.filter((e) => e.rental_state !== "Quote" || holding(e))
		.sort((a, b) => (a.starts_at < b.starts_at ? -1 : 1))
		.slice(0, 14);
});
const heldCount = computed(() => timeline.value.filter((e) => e.rental_state === "Quote").length);
function shortDate(value) {
	const d = new Date(String(value).replace(" ", "T"));
	return d.toLocaleDateString("fr-CA", { day: "numeric", month: "short" }).replace(".", "");
}

const STATUS_TEXT = { ok: "libre", partial: "partiellement réservé", full: "complet", none: "aucun parc" };

function cellLabel(row, day, c) {
	return `${row.item.item_name}, ${day.weekday} ${day.day} ${day.month} : ${Math.max(c.free, 0)} sur ${c.fleet} disponible${c.free > 1 ? "s" : ""}, ${STATUS_TEXT[c.status]}${c.held ? `, dont ${c.held} retenu${c.held > 1 ? "s" : ""} par un devis` : ""}`;
}

async function load() {
	loading.value = true;
	error.value = "";
	selected.value = null;
	try {
		const r = await frappe.call({
			method: "cortex_rental.api.v1.availability.get_matrix",
			type: "GET",
			args: {
					starts_at: `${start.value} 00:00:00`,
					ends_at: `${addDays(start.value, span.value)} 00:00:00`,
					search: search.value,
					category: category.value || undefined,
				},
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
// Détail d'un emprunt sans quitter la grille : client, factures, approbation et historique (dossier relié du serveur).
const expanded = ref(null);
const dossiers = ref({});
async function toggleBlock(b) {
	expanded.value = expanded.value === b.transaction ? null : b.transaction;
	if (!expanded.value || dossiers.value[b.transaction]) return;
	dossiers.value = { ...dossiers.value, [b.transaction]: "loading" };
	try {
		const r = await frappe.call({
			method: "cortex_rental.api.v1.dossier.get",
			type: "GET",
			args: { doctype: "Cortex Rental Transaction", name: b.transaction },
			silent: true,
		});
		dossiers.value = { ...dossiers.value, [b.transaction]: r.message };
	} catch (e) {
		dossiers.value = { ...dossiers.value, [b.transaction]: { error: true } };
	}
}
function dossierOf(b) {
	const d = dossiers.value[b.transaction];
	return d && d !== "loading" && !d.error ? d : null;
}
const INVOICE_STATUS = { Issued: "Émise", "Partially Paid": "Payée en partie", Paid: "Payée", Cancelled: "Annulée" };
const APPROVAL_STATUS = { Pending: "En attente", Approved: "Approuvée", Rejected: "Refusée" };

// Nouveau devis avec cet équipement à cette date : le serveur calcule les prix et retient le matériel s'il y en a.
function newQuote() {
	const s = selected.value;
	if (!s) return;
	const day = s.day.ymd;
	const free = Math.max(s.cell.free, 0);
	const dialog = new frappe.ui.Dialog({
		title: __("Nouveau devis"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "what",
				options: `<p><b>${frappe.utils.escape_html(s.row.item.item_name)}</b><br><span class="text-muted">${free} ${__("libre(s) sur")} ${s.cell.fleet} ${__("le")} ${day}${free ? "" : " · " + __("complet : le devis sera créé sans retenue du matériel")}</span></p>`,
			},
			{ fieldname: "customer", fieldtype: "Link", options: "Customer", label: __("Client"), reqd: 1 },
			{ fieldname: "qty", fieldtype: "Int", label: __("Quantité"), default: 1, reqd: 1 },
			{ fieldname: "starts", fieldtype: "Date", label: __("Début (09 h)"), default: day, reqd: 1 },
			{ fieldname: "ends", fieldtype: "Date", label: __("Fin (09 h)"), default: addDays(day, 1), reqd: 1 },
			{ fieldname: "project", fieldtype: "Data", label: __("Projet (facultatif)") },
		],
		primary_action_label: __("Créer le devis"),
		primary_action: async (v) => {
			if (v.ends <= v.starts) return frappe.msgprint(__("La fin doit être après le début."));
			if (!(v.qty >= 1)) return frappe.msgprint(__("Indiquez une quantité d'au moins 1."));
			dialog.disable_primary_action && dialog.disable_primary_action();
			try {
				const r = await frappe.call({
					method: "cortex_rental.api.v1.rentals.create_quote_draft",
					type: "POST",
					args: {
						customer_id: v.customer,
						starts_at: `${v.starts} 09:00:00`,
						ends_at: `${v.ends} 09:00:00`,
						project_name: v.project || "",
						items: JSON.stringify([{ item_code: s.row.item.item_code, quantity: v.qty }]),
					},
				});
				const name = (r.message || {}).entity_id;
				if (!name) return;
				const hold = await frappe.db.get_value("Cortex Rental Transaction", name, "hold_status");
				const held = hold && hold.message && hold.message.hold_status === "Active";
				frappe.show_alert({ message: held ? __("Devis {0} créé : le matériel est retenu.", [name]) : __("Devis {0} créé sans retenue (disponibilité insuffisante).", [name]), indicator: held ? "green" : "orange" }, 7);
				dialog.hide();
				frappe.set_route("Form", "Cortex Rental Transaction", name);
			} finally {
				dialog.enable_primary_action && dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
}

let timer = null;
function onSearch() {
	clearTimeout(timer);
	timer = setTimeout(load, 300);
}

function goCategory(value) {
	frappe.set_route("cortex-availability", value);
}
function setCategory(value) {
	const next = value || CATEGORY_ORDER[0] || "";
	if (next === category.value && items.value.length) return;
	category.value = next;
	load();
}

onMounted(() => {
	if (!category.value) category.value = CATEGORY_ORDER[0] || "";
	load();
});
defineExpose({ load, setCategory });
</script>

<template>
	<section class="cx-avail" aria-labelledby="cx-avail-title">
		<header class="cx-avail-head">
			<div>
				<h1 id="cx-avail-title" class="cx-avail-title">Disponibilité<span v-if="category"> · {{ __(category) }}</span></h1>
				<p class="cx-avail-sub">Unités libres de chaque équipement, jour par jour. Indicatif : le serveur revérifie au moment de réserver.</p>
			</div>
		</header>

		<nav class="cx-tabs" aria-label="Catégories d'équipement">
			<a
				v-for="c in CATEGORY_ORDER"
				:key="c"
				href="#"
				class="cx-tab"
				:class="{ active: c === category }"
				:aria-current="c === category ? 'page' : null"
				@click.prevent="goCategory(c)"
				>{{ __(c) }}</a
			>
		</nav>

		<div class="cx-avail-bar">
			<div class="cx-avail-nav" role="group" aria-label="Période">
				<button type="button" class="cx-btn cx-icon" aria-label="Période précédente" @click="shift(-1)">‹</button>
				<button type="button" class="cx-btn" @click="today">Aujourd'hui</button>
				<button type="button" class="cx-btn cx-icon" aria-label="Période suivante" @click="shift(1)">›</button>
				<span class="cx-avail-period" aria-live="polite">{{ periodLabel }}</span>
			</div>
			<input v-model="search" class="cx-search" type="search" aria-label="Rechercher un équipement" placeholder="Rechercher un équipement" @input="onSearch" />
			<select v-model.number="span" class="cx-span" aria-label="Période affichée" @change="load">
				<option v-for="s in SPANS" :key="s.days" :value="s.days">{{ s.label }}</option>
			</select>
			<ul class="cx-avail-legend" aria-label="Légende">
				<li><span class="cx-dot cx-dot-partial"></span> En partie réservé</li>
				<li><span class="cx-dot cx-dot-full"></span> Complet</li>
				<li><span class="cx-dot cx-dot-hold"></span> Retenu par un devis</li>
			</ul>
		</div>

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
					<tr v-if="!category" class="cx-group">
						<th :colspan="days.length + 1" scope="colgroup">{{ __(group) }}</th>
					</tr>
					<tr v-for="row in groupRows" :key="row.item.item_code">
						<th scope="row" class="cx-sticky">
							<span class="cx-name" :title="row.item.item_code">{{ row.item.item_name }}</span>
							<span class="cx-code">parc {{ row.item.fleet_quantity }}</span>
						</th>
						<td v-for="(c, i) in row.cells" :key="days[i].ymd" :class="{ 'cx-weekend': days[i].weekend }">
							<button
								type="button"
								class="cx-cell"
								:class="[`cx-cell-${c.status}`, { 'cx-cell-quote': c.quotes > 0 }]"
								:style="{ '--pct': fillPct(c) + '%', '--tot': holdPct(c) + '%' }"
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

		<section v-if="!loading && !error && timeline.length" class="cx-avail-timeline" aria-label="Locations et retenues de la période">
			<header>
				<h2>Sur la période</h2>
				<p>{{ timeline.length }} dossier{{ timeline.length > 1 ? "s" : "" }}<span v-if="heldCount"> · {{ heldCount }} devis qui retiennent du matériel</span></p>
			</header>
			<ul>
				<li v-for="e in timeline" :key="e.transaction">
					<a href="#" @click.prevent="openRental(e.transaction)">{{ e.transaction }}</a>
					<span class="cx-tl-state" :class="`cx-tl-${e.rental_state === 'Quote' ? 'hold' : 'book'}`">{{ e.rental_state === "Quote" ? "Devis · retenue" : STATE_LABELS[e.rental_state] || e.rental_state }}</span>
					<span class="cx-tl-main"><strong>{{ e.customer }}</strong> · {{ e.items.slice(0, 2).join(", ") }}<span v-if="e.items.length > 2"> +{{ e.items.length - 2 }}</span></span>
					<span class="cx-tl-when">{{ shortDate(e.starts_at) }} → {{ shortDate(e.ends_at) }}<span v-if="e.rental_state === 'Quote'"> · jusqu'au {{ shortDate(e.hold_until) }}</span></span>
				</li>
			</ul>
		</section>

		<aside v-if="selected" class="cx-avail-detail" aria-live="polite">
			<div class="cx-avail-detail-head">
				<strong>{{ selected.row.item.item_name }}</strong>
				<span>{{ selected.day.weekday }} {{ selected.day.day }} {{ selected.day.month }}</span>
				<button type="button" class="cx-btn" aria-label="Fermer le détail" @click="selected = null">Fermer</button>
			</div>
			<p>
				{{ Math.max(selected.cell.free, 0) }} libre{{ selected.cell.free > 1 ? "s" : "" }} sur {{ selected.cell.fleet }} ·
				{{ selected.cell.booked }} bloqué{{ selected.cell.booked > 1 ? "s" : "" }}<span v-if="selected.cell.held"> · {{ selected.cell.held }} retenu{{ selected.cell.held > 1 ? "s" : "" }} par un devis</span>
			</p>
			<button type="button" class="cx-btn cx-btn-primary cx-detail-cta" @click="newQuote">Créer un devis avec cet équipement ce jour-là</button>
			<p v-if="selected.cell.free <= 0" class="cx-avail-muted">Complet : un devis serait créé sans retenue du matériel.</p>
			<h4 class="cx-detail-sub">Locations ce jour-là</h4>
			<ul v-if="selected.cell.blocks.length" class="cx-avail-blocks">
				<li v-for="b in selected.cell.blocks" :key="b.transaction + b.starts_at" :class="{ open: expanded === b.transaction }">
					<button type="button" class="cx-block-btn" :aria-expanded="expanded === b.transaction" @click="toggleBlock(b)">
						<span class="cx-block-main">
							<b>{{ b.customer }}</b>
							<small>{{ b.transaction }} · {{ b.qty }} unité{{ b.qty > 1 ? "s" : "" }} · {{ b.starts_at.slice(5, 16) }} → {{ b.ends_at.slice(5, 16) }}</small>
						</span>
						<span class="cx-tl-state" :class="`cx-tl-${b.rental_state === 'Quote' ? 'hold' : 'book'}`">{{ b.rental_state === "Quote" ? (holding(b) ? "Devis · retenue" : "Devis") : STATE_LABELS[b.rental_state] || b.rental_state }}</span>
					</button>
					<div v-if="expanded === b.transaction" class="cx-block-detail">
						<p v-if="dossiers[b.transaction] === 'loading'" class="cx-avail-muted">Chargement…</p>
						<p v-else-if="!dossierOf(b)" class="cx-avail-muted">Le détail n'est pas disponible pour votre rôle.</p>
						<template v-else>
							<dl>
								<div v-if="dossierOf(b).customer"><dt>Client</dt><dd><a :href="'/app/customer/' + encodeURIComponent(dossierOf(b).customer.id)">{{ dossierOf(b).customer.name }}</a></dd></div>
								<div v-if="(dossierOf(b).invoices || []).length"><dt>Factures</dt><dd><span v-for="i in dossierOf(b).invoices" :key="i.id"><a :href="'/app/cortex-rental-invoice/' + encodeURIComponent(i.id)">{{ i.id }}</a> {{ INVOICE_STATUS[i.status] || i.status }}<template v-if="i.balance"> · solde {{ i.balance.toFixed(2) }} $</template><br /></span></dd></div>
								<div v-if="(dossierOf(b).approvals || []).length"><dt>Approbation</dt><dd><a :href="'/app/approval-request/' + encodeURIComponent(dossierOf(b).approvals[0].id)">{{ APPROVAL_STATUS[dossierOf(b).approvals[0].status] || dossierOf(b).approvals[0].status }}</a><template v-if="dossierOf(b).approvals[0].decided_by"> · {{ dossierOf(b).approvals[0].decided_by }}</template></dd></div>
								<div v-if="dossierOf(b).created_by"><dt>Créé par</dt><dd>{{ dossierOf(b).created_by }}</dd></div>
							</dl>
							<ul v-if="(dossierOf(b).timeline || []).length" class="cx-block-history">
								<li v-for="(e, n) in dossierOf(b).timeline.slice(0, 4)" :key="n"><b>{{ e.actor }}</b> · {{ e.text }} <small>{{ e.at }}</small></li>
							</ul>
						</template>
						<button type="button" class="cx-btn" @click="openRental(b.transaction)">Ouvrir la location</button>
					</div>
				</li>
			</ul>
			<p v-else class="cx-avail-muted">Aucune location sur cette journée : l'équipement est libre.</p>
		</aside>
	</section>
</template>

<style>
#page-cortex-availability .page-head {
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
.cx-tabs {
	display: flex;
	gap: 4px;
	margin: 14px 0 0;
	overflow-x: auto;
	scrollbar-width: none;
	border-bottom: 1px solid var(--line);
}
.cx-tab {
	flex: 0 0 auto;
	padding: 8px 12px;
	border-bottom: 2px solid transparent;
	color: var(--muted) !important;
	font-size: 13px;
	text-decoration: none !important;
	white-space: nowrap;
	transition: color 0.14s, border-color 0.14s, background 0.14s;
}
.cx-tab:hover {
	color: #09090b !important;
	background: #f4f4f5;
	border-radius: 8px 8px 0 0;
}
.cx-tab.active {
	color: #09090b !important;
	border-bottom-color: #09090b;
	font-weight: 600;
}
.cx-avail-head {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
	gap: 12px;
	align-items: flex-end;
}
.cx-avail-bar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 10px 12px;
	margin: 14px 0 12px;
}
.cx-search {
	height: 34px;
	width: 240px;
	max-width: 100%;
	padding: 0 12px;
	border: 1px solid var(--line);
	border-radius: 8px;
	background: #fff;
	font: inherit;
	font-size: 13px;
}
.cx-span {
	height: 34px;
	padding: 0 8px;
	border: 1px solid var(--line);
	border-radius: 8px;
	background: #fff;
	font: inherit;
	font-size: 13px;
}
.cx-icon {
	width: 34px;
	padding: 0;
	font-size: 18px;
	line-height: 1;
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
	gap: 4px 14px;
	list-style: none;
	margin: 0 0 0 auto;
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
.cx-dot-ok { background: #fff; border: 1px solid #a1a1aa; }
.cx-dot-partial { background: #e4e4e7; border: 1px solid #a1a1aa; }
.cx-dot-full { background: var(--full-bg); border: 1px solid var(--full); }
.cx-dot-quote { border: 1px dashed var(--muted); }
.cx-dot-hold { background: repeating-linear-gradient(135deg, rgba(180, 83, 9, 0.35) 0 3px, transparent 3px 6px); border: 1px solid #b45309; }
.cx-avail-scroll {
	overflow: auto;
	max-height: calc(100vh - 230px);
	min-height: 420px;
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
	padding: 3px 3px;
	border-bottom: 1px solid #f1f1f2;
	text-align: center;
	font-weight: 500;
}
.cx-avail-table thead th {
	position: sticky;
	top: 0;
	z-index: 2;
	min-width: 52px;
	background: #fafafa;
	color: var(--muted);
	font-size: 12px;
	white-space: nowrap;
	padding: 8px 3px;
}
.cx-avail-table thead .cx-today {
	box-shadow: inset 0 -2px 0 var(--ok);
	color: var(--ok);
}
.cx-avail-table .cx-today .cx-dn {
	color: var(--ok);
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
	min-width: 220px;
	max-width: 300px;
	padding: 4px 14px !important;
	text-align: left !important;
	display: table-cell;
	background: #fff;
	border-right: 1px solid var(--line);
}
thead .cx-sticky {
	background: #fafafa;
	z-index: 3;
}
.cx-name {
	display: inline-block;
	max-width: 230px;
	vertical-align: bottom;
	font-size: 13px;
	font-weight: 500;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cx-code {
	display: inline-block;
	margin-left: 8px;
	font-size: 11px;
	color: var(--muted);
}
.cx-group th {
	background: #fafafa;
	text-align: left;
	font-size: 11px;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--muted);
	padding: 6px 12px;
}
.cx-cell {
	width: 100%;
	min-width: 46px;
	height: 46px;
	border-radius: 8px;
	border: 1px solid transparent;
	background:
		linear-gradient(to top, rgba(63, 63, 70, 0.16) var(--pct, 0%), transparent var(--pct, 0%)),
		repeating-linear-gradient(135deg, rgba(180, 83, 9, 0.2) 0 4px, transparent 4px 8px) bottom / 100% var(--tot, 0%) no-repeat;
	color: #3f3f46;
	font: inherit;
	font-size: 14px;
	font-weight: 500;
	font-variant-numeric: tabular-nums;
	cursor: pointer;
	transition: transform 0.12s, box-shadow 0.12s;
}
.cx-cell:hover {
	background: #e4e4e7;
}
.cx-cell:focus-visible,
.cx-avail-scroll:focus-visible {
	outline: 2px solid var(--ok);
	outline-offset: 2px;
}
.cx-cell-ok { color: #71717a; }
.cx-cell-partial { color: #27272a; }
.cx-cell-full { background: var(--full-bg); color: var(--full); font-weight: 650; }
.cx-cell-none { color: #a1a1aa; }
.cx-cell-quote { border: 1px dashed var(--muted); }
.cx-cell[aria-pressed="true"] { box-shadow: 0 0 0 2px #09090b; }
.cx-avail-timeline {
	margin-top: 18px;
	padding: 14px 16px 6px;
	border: 1px solid var(--line);
	border-radius: 12px;
	background: #fff;
}
.cx-avail-timeline h2 {
	margin: 0;
	font-size: 15px;
	font-weight: 650;
}
.cx-avail-timeline header p {
	margin: 2px 0 8px;
	color: var(--muted);
	font-size: 12.5px;
}
.cx-avail-timeline ul {
	margin: 0;
	padding: 0;
	list-style: none;
}
.cx-avail-timeline li {
	display: grid;
	grid-template-columns: 150px 130px 1fr auto;
	gap: 4px 14px;
	align-items: center;
	padding: 9px 0;
	border-top: 1px solid #f1f1f2;
	font-size: 13px;
}
.cx-tl-state {
	justify-self: start;
	padding: 2px 9px;
	border-radius: 999px;
	font-size: 12px;
}
.cx-tl-book {
	background: #eef3ef;
	color: #3f6a52;
}
.cx-tl-hold {
	background: #fdf0e0;
	color: #8a4b00;
}
.cx-tl-main {
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cx-tl-when {
	color: var(--muted);
	white-space: nowrap;
}
@media (max-width: 760px) {
	.cx-avail-timeline li {
		grid-template-columns: 1fr auto;
	}
	.cx-tl-main {
		grid-column: 1 / -1;
		white-space: normal;
	}
}
.cx-avail-detail {
	position: fixed;
	top: 96px;
	right: 20px;
	bottom: 20px;
	z-index: 20;
	width: min(400px, calc(100vw - 32px));
	overflow-y: auto;
	padding: 16px 18px;
	border: 1px solid var(--line);
	border-radius: 14px;
	background: #fff;
	box-shadow: 0 16px 44px rgba(0, 0, 0, 0.14);
	animation: cx-rise 220ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
.cx-avail-detail-head {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 6px 10px;
}
.cx-avail-detail-head .cx-btn {
	margin-left: auto;
}
.cx-detail-cta {
	width: 100%;
	margin: 4px 0 8px;
}
.cx-detail-sub {
	margin: 18px 0 8px;
	font-size: 12px;
	font-weight: 650;
	letter-spacing: 0.05em;
	text-transform: uppercase;
	color: var(--muted);
}
.cx-avail-blocks {
	display: grid;
	gap: 8px;
	margin: 0;
	padding: 0;
	list-style: none;
	font-size: 13px;
}
.cx-avail-blocks li {
	border: 1px solid var(--line);
	border-radius: 10px;
	overflow: hidden;
}
.cx-block-btn {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	width: 100%;
	padding: 10px 12px;
	border: 0;
	background: transparent;
	text-align: left;
	cursor: pointer;
}
.cx-block-btn:hover {
	background: #f7f7f5;
}
.cx-block-main {
	display: grid;
	min-width: 0;
}
.cx-block-main small {
	color: var(--muted);
	font-size: 12px;
}
.cx-block-detail {
	display: grid;
	gap: 10px;
	padding: 4px 12px 12px;
	border-top: 1px solid var(--line);
}
.cx-block-detail dl {
	display: grid;
	gap: 8px;
	margin: 8px 0 0;
}
.cx-block-detail dt {
	color: var(--muted);
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.05em;
	text-transform: uppercase;
}
.cx-block-detail dd {
	margin: 0;
}
.cx-block-history {
	display: grid;
	gap: 4px;
	margin: 0;
	padding-left: 16px;
	font-size: 12.5px;
}
.cx-block-history small {
	color: var(--muted);
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
	height: 28px;
	margin-bottom: 8px;
	border-radius: 8px;
	background: linear-gradient(90deg, #f4f4f5 25%, #e9e9ec 37%, #f4f4f5 63%);
	background-size: 400% 100%;
	animation: cx-shimmer 1.4s linear infinite;
}
@media (max-width: 640px) {
	.cx-avail-detail {
		top: auto;
		right: 8px;
		bottom: 8px;
		left: 8px;
		width: auto;
		max-height: 72vh;
	}
	.cx-avail-scroll {
		max-height: none;
	}
	.cx-avail-legend {
		margin-left: 0;
	}
	.cx-search {
		width: 100%;
	}
	.cx-cell {
		min-width: 40px;
		height: 36px;
	}
	.cx-sticky {
		min-width: 104px;
		max-width: 112px;
		padding: 4px 8px !important;
	}
	.cx-name {
		display: block;
		max-width: none;
		white-space: normal;
		font-size: 12.5px;
		line-height: 1.25;
	}
	.cx-code {
		margin-left: 0;
	}
	.cx-avail-period {
		margin-left: 0;
		width: 100%;
	}
}
</style>
