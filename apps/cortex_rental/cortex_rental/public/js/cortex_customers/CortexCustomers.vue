<script setup>
import { ref, computed } from "vue";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexKpiCard from "../cortex_shared/CortexKpiCard.vue";
import CortexChart from "../cortex_shared/CortexChart.vue";
import CortexSlideOver from "../cortex_shared/CortexSlideOver.vue";
import CortexDocumentIngestor from "../cortex_shared/CortexDocumentIngestor.vue";
import CortexToast from "../cortex_shared/CortexToast.vue";
import { toast } from "../cortex_shared/toastBus.js";
import { ICONS } from "../cortex_shared/CortexIcons.js";

const CUSTOMERS_DATA = ref([
	{
		id: "CUST-001",
		name: "Dune 3 Productions Inc.",
		type: "Long Métrage Cinéma",
		contact: "Denis V. (Régie : Sarah M.)",
		email: "production@dune3montreal.com",
		phone: "+1 (514) 890-1234",
		riskScore: "Faible (VIP)",
		riskLevel: "low",
		insuranceStatus: "Valide",
		insurer: "Chubb Insurance Canada",
		policyNo: "CA-ENT-2026-99410",
		coverageAmount: 5000000,
		expiryDate: "2027-05-31",
		depositAmount: 50000,
		depositStatus: "Caution Bancaire Sécurisée",
		outstandingBalance: 124500,
		claimsCount: 0,
		notes: "Client grand compte prioritaire. Dégressivité 7j=3j accordée sur toutes les caméras ARRI.",
	},
	{
		id: "CUST-002",
		name: "HBO Series Montreal Studios",
		type: "Série TV Internationale",
		contact: "Marc L. (Directeur de Production)",
		email: "hbo.prod@montrealstudios.tv",
		phone: "+1 (514) 456-7890",
		riskScore: "Faible",
		riskLevel: "low",
		insuranceStatus: "Valide",
		insurer: "Travelers Entertainment",
		policyNo: "TRV-ENT-7781-A",
		coverageAmount: 3500000,
		expiryDate: "2027-03-15",
		depositAmount: 35000,
		depositStatus: "Retenue CB Validée",
		outstandingBalance: 68200,
		claimsCount: 1,
		notes: "1 câble BNC endommagé en juillet 2026 (remboursé sans contestation).",
	},
	{
		id: "CUST-003",
		name: "Indie Art Pictures",
		type: "Court Métrage Indépendant",
		contact: "Élodie B. (Réalisatrice-Productrice)",
		email: "elodie@indieartfilm.ca",
		phone: "+1 (438) 222-3344",
		riskScore: "Modéré (Attestation à renouveler)",
		riskLevel: "moderate",
		insuranceStatus: "Échéance Proche",
		insurer: "Intact Assurances",
		policyNo: "INT-8832-QC",
		coverageAmount: 500000,
		expiryDate: "2026-09-30",
		depositAmount: 10000,
		depositStatus: "Virement Séquestre",
		outstandingBalance: 14500,
		claimsCount: 0,
		notes: "Attestation expire le 30 septembre 2026. Alerte IA déclenchée pour renouvellement.",
	},
	{
		id: "CUST-004",
		name: "Apex Commercials Inc.",
		type: "Publicité & Clips",
		contact: "Thomas G. (Producteur Exécutif)",
		email: "tg@apexcommercials.com",
		phone: "+1 (514) 777-9900",
		riskScore: "Sous Surveillance",
		riskLevel: "high",
		insuranceStatus: "Expirée",
		insurer: "Desjardins Entreprises",
		policyNo: "DESJ-PUB-2025-EX",
		coverageAmount: 250000,
		expiryDate: "2026-08-31",
		depositAmount: 5000,
		depositStatus: "Caution Insuffisante",
		outstandingBalance: 32000,
		claimsCount: 2,
		notes: "Facture impayée depuis 45 jours. Sortie de matériel bloquée jusqu'à régularisation (`PRD-CLI`).",
	},
]);

const searchQuery = ref("");
const selectedCustomer = ref(null);
const isDrawerOpen = ref(false);
const showIngestor = ref(false);

const filteredCustomers = computed(() => {
	const q = searchQuery.value.trim().toLowerCase();
	if (!q) return CUSTOMERS_DATA.value;
	return CUSTOMERS_DATA.value.filter(
		(c) =>
			c.name.toLowerCase().includes(q) ||
			c.contact.toLowerCase().includes(q) ||
			c.insurer.toLowerCase().includes(q)
	);
});

// Graphiques
const riskDonutData = computed(() => {
	return {
		labels: ["Risque Faible / VIP", "Modéré", "Sous Surveillance / Bloqué"],
		datasets: [
			{
				data: [2, 1, 1],
				backgroundColor: ["#059669", "#d97706", "#dc2626"],
				borderWidth: 0,
				cutout: "70%",
			},
		],
	};
});

const coverageBarData = computed(() => {
	return {
		labels: ["Dune 3", "HBO Series", "Indie Art", "Apex Pub"],
		datasets: [
			{
				label: "Plafond d'Assurance (M$ CAD)",
				data: [5.0, 3.5, 0.5, 0.25],
				backgroundColor: "#059669",
				borderRadius: 4,
			},
			{
				label: "Encours de Location (k$ CAD)",
				data: [0.12, 0.068, 0.014, 0.032],
				backgroundColor: "#2563eb",
				borderRadius: 4,
			},
		],
	};
});

function openCustomerDetail(c) {
	selectedCustomer.value = c;
	isDrawerOpen.value = true;
}

function handleExtractedInsurance(data) {
	toast.success("✓ Attestation d'assurance extraite par l'IA ! Mise à jour des garanties.");
	if (selectedCustomer.value) {
		selectedCustomer.value.insurer = data.data.insurer;
		selectedCustomer.value.policyNo = data.data.policyNumber;
		selectedCustomer.value.insuranceStatus = "Valide";
	}
	showIngestor.value = false;
}
</script>

<template>
	<div class="cortex-app cx-app">
		<CortexToast />
		<CortexPageHeader
			title="Clients & Risque Assurance"
			subtitle="Onboarding des productions, scoring solvabilité IA, vérification des polices d'assurance et cautions."
		>
			<template #actions>
				<button class="cx-btn" @click="showIngestor = !showIngestor">
					<span class="cx-icon-sm" v-html="ICONS.fileText"></span>
					<span>{{ showIngestor ? 'Fermer Analyseur' : 'Ingérer Attestation PDF' }}</span>
				</button>
				<button class="cx-btn cx-btn-primary" @click="toast.info('Formulaire d\'onboarding client prêt.')">
					+ Nouvelle Société de Production
				</button>
			</template>
		</CortexPageHeader>

		<!-- Ingestor IA intégré si actif -->
		<div v-if="showIngestor" style="margin-bottom: var(--space-4)">
			<CortexDocumentIngestor
				mode="insurance"
				title="Ingestion IA de Police d'Assurance de Tournage"
				@extracted="handleExtractedInsurance"
			/>
		</div>

		<!-- Grille KPI -->
		<div class="cx-kpi-grid" style="margin-bottom: var(--space-4)">
			<CortexKpiCard
				title="Productions Actives"
				value="4 comptes"
				:trend="12.0"
				badge="Actif"
				:sparkline="[2, 3, 3, 4, 4, 4]"
			/>
			<CortexKpiCard
				title="Cautions Bancaires Sécurisées"
				value="95 000 $"
				:trend="8.5"
				badge="Séquestre"
				:sparkline="[60, 75, 80, 85, 90, 95]"
			/>
			<CortexKpiCard
				title="Garanties d'Assurance Totales"
				value="9.25 M$"
				:trend="0"
				badge="Couvert"
				:sparkline="[8, 8.5, 9, 9, 9.25, 9.25]"
			/>
			<CortexKpiCard
				title="Alertes de Risque / Expiration"
				value="2 alertes"
				:trend="-1"
				badge="À traiter"
				:sparkline="[3, 3, 2, 2, 2, 2]"
			/>
		</div>

		<!-- Graphiques Clients & Risque -->
		<div class="cx-charts-grid" style="margin-bottom: var(--space-4)">
			<div class="cx-chart-card cx-surface">
				<div class="cx-chart-header">
					<div>
						<h3 class="cx-chart-title">Plafonds d'Assurance vs Encours</h3>
						<p class="cx-chart-subtitle">Couverture de responsabilité civile et bris de machine par production</p>
					</div>
					<span class="cx-badge cx-badge-success">Solvabilité</span>
				</div>
				<div class="cx-chart-container">
					<CortexChart type="bar" :data={labels:coverageBarData.labels,datasets:coverageBarData.datasets} :height="200" />
				</div>
			</div>

			<div class="cx-chart-card cx-surface">
				<div class="cx-chart-header">
					<div>
						<h3 class="cx-chart-title">Scoring Risque Portefeuille</h3>
						<p class="cx-chart-subtitle">Indice de solvabilité et conformité des comptes</p>
					</div>
					<span class="cx-badge cx-badge-info">Audit IA</span>
				</div>
				<div class="cx-donut-chart" style="margin: 0 auto">
					<CortexChart type="doughnut" :data="riskDonutData" :height="170" />
				</div>
			</div>
		</div>

		<!-- Barre de Recherche -->
		<div class="cx-customers-toolbar cx-surface">
			<div class="cx-search-input-wrap">
				<span class="cx-icon-sm" v-html="ICONS.search || ICONS.shield"></span>
				<input
					v-model="searchQuery"
					type="text"
					class="cx-search-input"
					placeholder="Rechercher par nom de production, contact, compagnie d'assurance…"
				/>
			</div>
			<div class="cx-toolbar-actions">
				<span class="cx-text-meta">Affichage de {{ filteredCustomers.length }} sociétés</span>
			</div>
		</div>

		<!-- Tableau des Clients -->
		<div class="cx-surface cx-table-card">
			<table class="cx-table">
				<thead>
					<tr>
						<th>Société de Production</th>
						<th>Contact &amp; Rôle</th>
						<th>Police d'Assurance</th>
						<th style="text-align: right">Caution Sécurisée</th>
						<th style="text-align: center">Score Risque IA</th>
						<th style="text-align: right">Actions</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="c in filteredCustomers"
						:key="c.id"
						class="cx-clickable-row"
						@click="openCustomerDetail(c)"
					>
						<td>
							<div class="cx-customer-name">{{ c.name }}</div>
							<div class="cx-customer-meta">{{ c.type }} • <code>{{ c.id }}</code></div>
						</td>
						<td>
							<div class="cx-contact-name">{{ c.contact }}</div>
							<div class="cx-contact-meta">{{ c.email }}</div>
						</td>
						<td>
							<div>{{ c.insurer }}</div>
							<div class="cx-insurance-meta">
								<span
									class="cx-badge"
									:class="c.insuranceStatus === 'Valide' ? 'cx-badge-success' : c.insuranceStatus === 'Échéance Proche' ? 'cx-badge-warning' : 'cx-badge-danger'"
								>
									{{ c.insuranceStatus }}
								</span>
								<span>Jusqu'au {{ c.expiryDate }}</span>
							</div>
						</td>
						<td style="text-align: right; font-family: var(--font-mono); font-weight: 600">
							{{ c.depositAmount.toLocaleString() }} $
						</td>
						<td style="text-align: center">
							<span
								class="cx-badge"
								:class="c.riskLevel === 'low' ? 'cx-badge-success' : c.riskLevel === 'moderate' ? 'cx-badge-warning' : 'cx-badge-danger'"
							>
								{{ c.riskScore }}
							</span>
						</td>
						<td style="text-align: right">
							<button class="cx-btn cx-btn-ghost" @click.stop="openCustomerDetail(c)">
								Fiche ↗
							</button>
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<!-- Slide-Over Drawer Fiche Client & Assurance (Divulgation Progressive) -->
		<CortexSlideOver
			:open="isDrawerOpen"
			:title="selectedCustomer ? selectedCustomer.name : ''"
			:subtitle="selectedCustomer ? selectedCustomer.id + ' • ' + selectedCustomer.type : ''"
			width="620px"
			@close="isDrawerOpen = false"
		>
			<template v-if="selectedCustomer">
				<!-- Indicateurs Clés Client -->
				<div class="cx-drawer-kpi-grid">
					<div class="cx-drawer-tile">
						<span class="cx-text-label">Plafond Garantie Assurance</span>
						<div class="cx-drawer-val">{{ selectedCustomer.coverageAmount.toLocaleString() }} $ CAD</div>
					</div>
					<div class="cx-drawer-tile">
						<span class="cx-text-label">Caution Actuelle</span>
						<div class="cx-drawer-val">{{ selectedCustomer.depositAmount.toLocaleString() }} $ CAD</div>
					</div>
					<div class="cx-drawer-tile">
						<span class="cx-text-label">Encours Facturation</span>
						<div class="cx-drawer-val">{{ selectedCustomer.outstandingBalance.toLocaleString() }} $ CAD</div>
					</div>
					<div class="cx-drawer-tile">
						<span class="cx-text-label">Historique Sinistres</span>
						<div class="cx-drawer-val">{{ selectedCustomer.claimsCount }} sinistre(s)</div>
					</div>
				</div>

				<!-- Détails Assurance de Tournage (PRD-CLI) -->
				<div class="cx-section-block">
					<h4 class="cx-section-title">
						<span class="cx-icon-sm cx-emerald" v-html="ICONS.shield"></span>
						Police d'Assurance Production (Obligatoire Contrat)
					</h4>
					<div class="cx-insurance-box">
						<div class="cx-ins-row">
							<span class="cx-text-label">Compagnie :</span>
							<span class="cx-ins-val">{{ selectedCustomer.insurer }}</span>
						</div>
						<div class="cx-ins-row">
							<span class="cx-text-label">Numéro de Police :</span>
							<span class="cx-ins-val"><code>{{ selectedCustomer.policyNo }}</code></span>
						</div>
						<div class="cx-ins-row">
							<span class="cx-text-label">Période de Validité :</span>
							<span class="cx-ins-val">Valable jusqu'au {{ selectedCustomer.expiryDate }}</span>
						</div>
						<div class="cx-ins-row">
							<span class="cx-text-label">Bénéficiaire Additionnel :</span>
							<span class="cx-badge cx-badge-success">Cortex Rentals Inc. Valide</span>
						</div>
					</div>
				</div>

				<!-- Contacts et Coordonnées -->
				<div class="cx-section-block">
					<h4 class="cx-section-title">Contacts Équipe de Tournage</h4>
					<div class="cx-contact-card">
						<div><strong>Contact Principal :</strong> {{ selectedCustomer.contact }}</div>
						<div><strong>Email :</strong> {{ selectedCustomer.email }}</div>
						<div><strong>Téléphone Urgence Plateau :</strong> {{ selectedCustomer.phone }}</div>
					</div>
				</div>

				<!-- Notes Opérationnelles & IA -->
				<div class="cx-section-block">
					<h4 class="cx-section-title">
						<span class="cx-icon-sm cx-emerald" v-html="ICONS.sparkles"></span>
						Recommandations &amp; Historique IA
					</h4>
					<p class="cx-notes-text">{{ selectedCustomer.notes }}</p>
				</div>
			</template>

			<template #footer>
				<button class="cx-btn cx-btn-ghost" @click="isDrawerOpen = false">Fermer</button>
				<button class="cx-btn cx-btn-primary" @click="toast.success('Fiche client mise à jour dans ERPNext.')">
					Valider Dossier Client
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

.cx-customers-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--space-3) var(--space-4);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	margin-bottom: var(--space-4);
	gap: var(--space-4);
}

.cx-search-input-wrap {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	background: var(--cortex-surface-muted);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: 4px var(--space-3);
	flex: 1;
	max-width: 420px;
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

.cx-customer-name {
	font-weight: 500;
	color: var(--cortex-text-primary);
}
.cx-customer-meta {
	font-size: 11px;
	color: var(--cortex-text-muted);
}

.cx-contact-name {
	font-size: 12.5px;
	color: var(--cortex-text-primary);
}
.cx-contact-meta {
	font-size: 11px;
	color: var(--cortex-text-muted);
}

.cx-insurance-meta {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	font-size: 11px;
	color: var(--cortex-text-muted);
	margin-top: 2px;
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
	font-size: 14px;
	font-weight: 600;
	font-family: var(--font-mono);
	color: var(--cortex-text-primary);
	margin-top: 2px;
}

.cx-insurance-box {
	background: var(--cortex-surface-muted);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-3);
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
}

.cx-ins-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	font-size: 12px;
}

.cx-ins-val {
	font-weight: 500;
	color: var(--cortex-text-primary);
}

.cx-contact-card {
	padding: var(--space-3);
	background: var(--cortex-surface-muted);
	border-radius: var(--radius-md);
	font-size: 12px;
	display: flex;
	flex-direction: column;
	gap: 4px;
	color: var(--cortex-text-primary);
}

.cx-notes-text {
	font-size: 12px;
	color: var(--cortex-text-primary);
	line-height: 1.4;
	background: var(--cortex-surface-muted);
	padding: var(--space-3);
	border-radius: var(--radius-md);
	margin: 0;
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
