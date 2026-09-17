<script setup>
import { ref, computed } from "vue";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexKpiCard from "../cortex_shared/CortexKpiCard.vue";
import CortexChart from "../cortex_shared/CortexChart.vue";
import CortexSlideOver from "../cortex_shared/CortexSlideOver.vue";
import CortexToast from "../cortex_shared/CortexToast.vue";
import { toast } from "../cortex_shared/toastBus.js";
import { ICONS } from "../cortex_shared/CortexIcons.js";

// Données de la flotte cinéma
const FLEET_DATA = ref([
	{
		code: "ARRI-ALX35",
		name: "ARRI Alexa 35 Cinema Camera Package",
		category: "Cameras",
		dailyRate: 1500,
		replacementValue: 85000,
		totalUnits: 3,
		availableUnits: 1,
		status: "Actif",
		ownerType: "Interne",
		ownerName: "Cortex Rentals",
		consignmentRate: 0,
		serials: [
			{ sn: "SN-ALX-001", status: "En tournage", location: "Dune 3 Productions", hours: 412, nextService: "2026-11-15", health: "Excellente" },
			{ sn: "SN-ALX-002", status: "Disponible", location: "Entrepôt Principal (Zone A)", hours: 185, nextService: "2027-01-20", health: "Excellente" },
			{ sn: "SN-ALX-003", status: "Maintenance", location: "Atelier Optique & Capteur", hours: 890, nextService: "2026-09-25", health: "Calibration requise" },
		],
		maintenanceNote: "Capteur nettoyé il y a 40h. Prochaine calibration colorimétrique recommandée dans 110h.",
	},
	{
		code: "COOKE-S4I-SET",
		name: "Cooke S4/i Prime Lens Set T2.0 (18, 25, 32, 50, 75, 100mm)",
		category: "Lenses",
		dailyRate: 1200,
		replacementValue: 120000,
		totalUnits: 2,
		availableUnits: 1,
		status: "Actif",
		ownerType: "Consignation Tiers",
		ownerName: "Panavision Montreal (Tiers #84)",
		consignmentRate: 25,
		serials: [
			{ sn: "SN-CKE-001", status: "En tournage", location: "Dune 3 Productions", hours: 320, nextService: "2026-12-01", health: "Parfaite" },
			{ sn: "SN-CKE-002", status: "Disponible", location: "Coffre-fort Optiques (Zone B)", hours: 140, nextService: "2027-03-10", health: "Parfaite" },
		],
		maintenanceNote: "Bagues de point vérifiées au banc collimateur le 10 août 2026.",
	},
	{
		code: "APUTURE-1200D",
		name: "Aputure Electro Storm 1200D Pro Daylight LED",
		category: "Lighting",
		dailyRate: 350,
		replacementValue: 9500,
		totalUnits: 4,
		availableUnits: 2,
		status: "Actif",
		ownerType: "Interne",
		ownerName: "Cortex Rentals",
		consignmentRate: 0,
		serials: [
			{ sn: "SN-APT-001", status: "En tournage", location: "Studio MTL Plateaux", hours: 540, nextService: "2026-10-10", health: "Normale" },
			{ sn: "SN-APT-002", status: "En tournage", location: "Studio MTL Plateaux", hours: 490, nextService: "2026-10-10", health: "Normale" },
			{ sn: "SN-APT-003", status: "Disponible", location: "Rayon Lumière (Zone L)", hours: 210, nextService: "2027-02-01", health: "Excellente" },
			{ sn: "SN-APT-004", status: "Disponible", location: "Rayon Lumière (Zone L)", hours: 190, nextService: "2027-02-01", health: "Excellente" },
		],
		maintenanceNote: "Firmware v2.4 mis à jour. Ballast vérifié.",
	},
	{
		code: "BNC-50FT",
		name: "12G-SDI 4K UHD BNC Cable 50ft (Belden 1505A)",
		category: "Accessories",
		dailyRate: 15,
		replacementValue: 120,
		totalUnits: 150,
		availableUnits: 82,
		status: "Actif",
		ownerType: "Interne",
		ownerName: "Cortex Rentals",
		consignmentRate: 0,
		serials: [],
		maintenanceNote: "Testé au réflectomètre lors de chaque retour d'atelier.",
	},
	{
		code: "C-STAND-40",
		name: "Avenger 40 inch Turtle Base C-Stand with Grip Head & Arm",
		category: "Grip",
		dailyRate: 18,
		replacementValue: 280,
		totalUnits: 80,
		availableUnits: 45,
		status: "Actif",
		ownerType: "Interne",
		ownerName: "Cortex Rentals",
		consignmentRate: 0,
		serials: [],
		maintenanceNote: "Ressorts et molettes inspectés mensuellement.",
	},
]);

const activeCategory = ref("Toutes");
const searchQuery = ref("");
const selectedItem = ref(null);
const isDrawerOpen = ref(false);

const CATEGORIES = ["Toutes", "Cameras", "Lenses", "Lighting", "Grip", "Accessories"];

const filteredFleet = computed(() => {
	return FLEET_DATA.value.filter((item) => {
		const matchesCat = activeCategory.value === "Toutes" || item.category === activeCategory.value;
		const matchesSearch =
			!searchQuery.value ||
			item.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
			item.code.toLowerCase().includes(searchQuery.value.toLowerCase());
		return matchesCat && matchesSearch;
	});
});

// Graphiques du parc
const fleetDonutData = computed(() => {
	return {
		labels: ["Caméras", "Optiques", "Éclairage", "Grip & Câblage"],
		datasets: [
			{
				data: [3, 2, 4, 230],
				backgroundColor: ["#059669", "#2563eb", "#d97706", "#71717a"],
				borderWidth: 0,
				cutout: "70%",
			},
		],
	};
});

const fleetUsageBarData = computed(() => {
	return {
		labels: ["ARRI ALX35 #1", "ARRI ALX35 #3", "Cooke S4/i #1", "Aputure #1", "Aputure #2"],
		datasets: [
			{
				label: "Heures d'utilisation (Seuil service 500h)",
				data: [412, 890, 320, 540, 490],
				backgroundColor: ["#059669", "#dc2626", "#059669", "#d97706", "#059669"],
				borderRadius: 4,
			},
		],
	};
});

function openItemDetail(item) {
	selectedItem.value = item;
	isDrawerOpen.value = true;
}

function triggerAiHealthScan() {
	toast.info("Agent Onyx analyse la télémétrie des capteurs et cycles d'utilisation…");
	setTimeout(() => {
		toast.success("✓ Diagnostic IA terminé : ARRI ALX-003 prioritaire pour calibration capteur.");
	}, 800);
}
</script>

<template>
	<div class="cortex-app cx-app">
		<CortexToast />
		<CortexPageHeader
			title="Parc Matériel & Maintenance"
			subtitle="Gestion de flotte cinéma, numéros de série, entretien préventif et consignation tiers."
		>
			<template #actions>
				<button class="cx-btn" @click="triggerAiHealthScan">
					<span class="cx-icon-sm" v-html="ICONS.sparkles"></span>
					<span>Scan Santé IA</span>
				</button>
				<button class="cx-btn cx-btn-primary" @click="toast.info('Formulaire d\'ajout de profil prêt.')">
					+ Nouveau Profil Matériel
				</button>
			</template>
		</CortexPageHeader>

		<!-- Grille KPI -->
		<div class="cx-kpi-grid" style="margin-bottom: var(--space-4)">
			<CortexKpiCard
				title="Unités Gérées au Parc"
				value="239"
				:trend="5.2"
				badge="Actif"
				:sparkline="[220, 225, 230, 235, 238, 239]"
			/>
			<CortexKpiCard
				title="Taux de Disponibilité"
				value="58.6%"
				:trend="2.1"
				badge="Entrepôt"
				:sparkline="[65, 62, 59, 57, 56, 58]"
			/>
			<CortexKpiCard
				title="En Maintenance / Révision"
				value="1 unité"
				:trend="-50.0"
				badge="Priorité"
				:sparkline="[4, 3, 2, 3, 2, 1]"
			/>
			<CortexKpiCard
				title="Consignation Tiers"
				value="25% comm."
				:trend="0"
				badge="PRD-CON Sécurisé"
				:sparkline="[25, 25, 25, 25, 25, 25]"
			/>
		</div>

		<!-- Graphiques de la Flotte -->
		<div class="cx-charts-grid" style="margin-bottom: var(--space-4)">
			<div class="cx-chart-card cx-surface">
				<div class="cx-chart-header">
					<div>
						<h3 class="cx-chart-title">Heures de Tournage &amp; Cycles Préventifs</h3>
						<p class="cx-chart-subtitle">Indicateur d'usure des capteurs et lampes (Seuil d'alerte à 500h)</p>
					</div>
					<span class="cx-badge cx-badge-warning">Maintenance IA</span>
				</div>
				<div class="cx-chart-container">
					<CortexChart type="bar" :data={labels:fleetUsageBarData.labels,datasets:fleetUsageBarData.datasets} :height="200" />
				</div>
			</div>

			<div class="cx-chart-card cx-surface">
				<div class="cx-chart-header">
					<div>
						<h3 class="cx-chart-title">Allocation du Parc</h3>
						<p class="cx-chart-subtitle">Répartition par catégorie d'équipement</p>
					</div>
					<span class="cx-badge cx-badge-info">Inventaire</span>
				</div>
				<div class="cx-donut-chart" style="margin: 0 auto">
					<CortexChart type="doughnut" :data="fleetDonutData" :height="170" />
				</div>
			</div>
		</div>

		<!-- Filtres et Recherche -->
		<div class="cx-fleet-toolbar cx-surface">
			<div class="cx-category-chips">
				<button
					v-for="cat in CATEGORIES"
					:key="cat"
					class="cx-chip"
					:class="{ 'is-active': activeCategory === cat }"
					@click="activeCategory = cat"
				>
					{{ cat }}
				</button>
			</div>

			<div class="cx-search-input-wrap">
				<span class="cx-icon-sm" v-html="ICONS.search || ICONS.camera"></span>
				<input
					v-model="searchQuery"
					type="text"
					class="cx-search-input"
					placeholder="Rechercher par référence, nom…"
				/>
			</div>
		</div>

		<!-- Tableau SaaS de la Flotte -->
		<div class="cx-surface cx-table-card">
			<table class="cx-table">
				<thead>
					<tr>
						<th>Code Profil</th>
						<th>Équipement &amp; Configuration</th>
						<th>Catégorie</th>
						<th style="text-align: center">Disponibilité</th>
						<th style="text-align: right">Tarif Jour</th>
						<th>Propriété / Consignation</th>
						<th style="text-align: right">Actions</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="item in filteredFleet"
						:key="item.code"
						class="cx-clickable-row"
						@click="openItemDetail(item)"
					>
						<td><code>{{ item.code }}</code></td>
						<td>
							<div class="cx-item-name">{{ item.name }}</div>
							<div class="cx-item-meta">{{ item.serials.length ? item.serials.length + ' unités sérialisées' : 'Article en vrac' }}</div>
						</td>
						<td><span class="cx-badge cx-badge-neutral">{{ item.category }}</span></td>
						<td style="text-align: center">
							<span
								class="cx-badge"
								:class="item.availableUnits > 0 ? 'cx-badge-success' : 'cx-badge-danger'"
							>
								{{ item.availableUnits }} / {{ item.totalUnits }} dispo
							</span>
						</td>
						<td style="text-align: right; font-family: var(--font-mono); font-weight: 600">
							{{ item.dailyRate }} $
						</td>
						<td>
							<span v-if="item.ownerType === 'Interne'" class="cx-badge cx-badge-neutral">Parc Interne</span>
							<span v-else class="cx-badge cx-badge-warning" title="Consignation Tiers">{{ item.ownerName }}</span>
						</td>
						<td style="text-align: right">
							<button class="cx-btn cx-btn-ghost" @click.stop="openItemDetail(item)">
								Détails ↗
							</button>
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<!-- Slide-Over Drawer de Détail & Maintenance (Divulgation Progressive) -->
		<CortexSlideOver
			:open="isDrawerOpen"
			:title="selectedItem ? selectedItem.name : ''"
			:subtitle="selectedItem ? selectedItem.code + ' • ' + selectedItem.category : ''"
			width="620px"
			@close="isDrawerOpen = false"
		>
			<template v-if="selectedItem">
				<!-- Section Tarifs et Valeur -->
				<div class="cx-drawer-kpi-grid">
					<div class="cx-drawer-tile">
						<span class="cx-text-label">Tarif Journalier</span>
						<div class="cx-drawer-val">{{ selectedItem.dailyRate }} $ / jour</div>
					</div>
					<div class="cx-drawer-tile">
						<span class="cx-text-label">Valeur de Remplacement</span>
						<div class="cx-drawer-val">{{ selectedItem.replacementValue.toLocaleString() }} $</div>
					</div>
					<div class="cx-drawer-tile">
						<span class="cx-text-label">Règle Tarifaire</span>
						<div class="cx-drawer-val">7 jours = 3 jours</div>
					</div>
					<div class="cx-drawer-tile">
						<span class="cx-text-label">Propriétaire</span>
						<div class="cx-drawer-val">{{ selectedItem.ownerType }}</div>
					</div>
				</div>

				<!-- Volet Consignation Tiers (PRD-CON) -->
				<div v-if="selectedItem.ownerType !== 'Interne'" class="cx-consignment-box">
					<div class="cx-consignment-header">
						<span class="cx-badge cx-badge-warning">Protocole PRD-CON</span>
						<span class="cx-text-meta">Isolation stricte de l'identité locataire</span>
					</div>
					<p class="cx-consignment-desc">
						Cet équipement appartient à <strong>{{ selectedItem.ownerName }}</strong>.
						Une commission de <strong>{{ selectedItem.consignmentRate }}%</strong> est automatiquement créditée sur son compte lors de chaque sortie, sans révéler les noms des productions locataires.
					</p>
				</div>

				<!-- Carnet d'Entretien & Maintenance IA -->
				<div class="cx-section-block">
					<h4 class="cx-section-title">
						<span class="cx-icon-sm cx-emerald" v-html="ICONS.sparkles"></span>
						Diagnostic d'Entretien Préventif IA
					</h4>
					<div class="cx-maintenance-card">
						<p class="cx-maintenance-text">{{ selectedItem.maintenanceNote }}</p>
						<span class="cx-badge cx-badge-info">Indice de Santé : 94%</span>
					</div>
				</div>

				<!-- Liste des Numéros de Série Physiques -->
				<div v-if="selectedItem.serials.length" class="cx-section-block">
					<h4 class="cx-section-title">Unités Physiques Sérialisées ({{ selectedItem.serials.length }})</h4>
					<table class="cx-table cx-table-sm">
						<thead>
							<tr>
								<th>N° de Série</th>
								<th>Statut Actuel</th>
								<th>Emplacement / Tournage</th>
								<th>Heures</th>
								<th>Santé</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="sn in selectedItem.serials" :key="sn.sn">
								<td><code>{{ sn.sn }}</code></td>
								<td>
									<span
										class="cx-badge"
										:class="sn.status === 'Disponible' ? 'cx-badge-success' : sn.status === 'Maintenance' ? 'cx-badge-danger' : 'cx-badge-info'"
									>
										{{ sn.status }}
									</span>
								</td>
								<td class="cx-text-meta">{{ sn.location }}</td>
								<td style="font-family: var(--font-mono)">{{ sn.hours }} h</td>
								<td>
									<span class="cx-health-tag" :class="{ 'is-warn': sn.health.includes('requise') }">
										{{ sn.health }}
									</span>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</template>

			<template #footer>
				<button class="cx-btn cx-btn-ghost" @click="isDrawerOpen = false">Fermer</button>
				<button class="cx-btn cx-btn-primary" @click="toast.success('Fiche matériel synchronisée avec ERPNext.')">
					Enregistrer Modifications
				</button>
			</template>
		</CortexSlideOver>
	</div>
</template>

<style scoped>
.cx-app {
	padding: 0 var(--space-6) var(--space-8);
}

.cx-kpi-grid {
	display: grid;
	grid-template-columns: repeat(4, 1fr);
	gap: var(--space-3);
}

.cx-charts-grid {
	display: grid;
	grid-template-columns: 2fr 1fr;
	gap: var(--space-4);
}

.cx-chart-card {
	padding: var(--space-4);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	background: var(--cortex-surface);
}

.cx-chart-header {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	margin-bottom: var(--space-3);
}

.cx-chart-title {
	font-size: 13.5px;
	font-weight: 600;
	color: var(--cortex-text-primary);
	margin: 0;
}

.cx-chart-subtitle {
	font-size: 11px;
	color: var(--cortex-text-muted);
	margin: 2px 0 0;
}

.cx-chart-container {
	position: relative;
	min-height: 200px;
}

.cx-fleet-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--space-3) var(--space-4);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	margin-bottom: var(--space-4);
	gap: var(--space-4);
	flex-wrap: wrap;
}

.cx-category-chips {
	display: flex;
	gap: var(--space-2);
	flex-wrap: wrap;
}

.cx-chip.is-active {
	background: var(--cortex-primary-600);
	border-color: var(--cortex-primary-600);
	color: var(--cortex-inverse);
}

.cx-search-input-wrap {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	background: var(--cortex-surface-muted);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: 4px var(--space-3);
	min-width: 260px;
}

.cx-search-input {
	border: none;
	background: transparent;
	font-size: 12.5px;
	outline: none;
	width: 100%;
}

.cx-table-card {
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	overflow: hidden;
}

.cx-clickable-row {
	cursor: pointer;
	transition: background 0.1s ease;
}
.cx-clickable-row:hover {
	background: var(--cortex-surface-muted);
}

.cx-item-name {
	font-weight: 500;
	color: var(--cortex-text-primary);
}
.cx-item-meta {
	font-size: 11px;
	color: var(--cortex-text-muted);
}

/* Drawer Detail Styles */
.cx-drawer-kpi-grid {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: var(--space-3);
	margin-bottom: var(--space-5);
}

.cx-drawer-tile {
	padding: var(--space-3);
	background: var(--cortex-surface-muted);
	border-radius: var(--radius-md);
	border: 1px solid var(--cortex-border);
}

.cx-drawer-val {
	font-size: 14.5px;
	font-weight: 600;
	font-family: var(--font-mono);
	color: var(--cortex-text-primary);
	margin-top: 2px;
}

.cx-consignment-box {
	background: var(--cortex-surface-muted);
	border: 1px solid var(--cortex-border);
	border-left: 3px solid var(--cortex-primary-600);
	border-radius: var(--radius-md);
	padding: var(--space-3);
	margin-bottom: var(--space-5);
}

.cx-consignment-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: var(--space-2);
}

.cx-consignment-desc {
	font-size: 12px;
	color: var(--cortex-text-primary);
	margin: 0;
	line-height: 1.4;
}

.cx-section-block {
	margin-bottom: var(--space-5);
}

.cx-section-title {
	font-size: 13px;
	font-weight: 600;
	color: var(--cortex-text-primary);
	margin: 0 0 var(--space-2);
	display: flex;
	align-items: center;
	gap: 6px;
}

.cx-maintenance-card {
	padding: var(--space-3);
	background: var(--cortex-surface-muted);
	border-radius: var(--radius-md);
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-3);
}

.cx-maintenance-text {
	font-size: 12px;
	color: var(--cortex-text-primary);
	margin: 0;
	line-height: 1.4;
}

.cx-health-tag {
	font-size: 11px;
	color: var(--cortex-primary-700);
}
.cx-health-tag.is-warn {
	color: #dc2626;
	font-weight: 600;
}

.cx-emerald {
	color: var(--cortex-primary-600);
}

@media (max-width: 1024px) {
	.cx-kpi-grid {
		grid-template-columns: repeat(2, 1fr);
	}
	.cx-charts-grid {
		grid-template-columns: 1fr;
	}
}
@media (max-width: 640px) {
	.cx-kpi-grid {
		grid-template-columns: 1fr;
	}
}
</style>
