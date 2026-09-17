<script setup>
import { ref, computed } from "vue";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexKpiCard from "../cortex_shared/CortexKpiCard.vue";
import CortexSlideOver from "../cortex_shared/CortexSlideOver.vue";
import CortexToast from "../cortex_shared/CortexToast.vue";
import { toast } from "../cortex_shared/toastBus.js";
import { ICONS } from "../cortex_shared/CortexIcons.js";

const activeTab = ref("approvals"); // 'approvals' | 'audit'

// File des Approbations Humaines (PRD-AI / PRD-ARCH)
const APPROVAL_REQUESTS = ref([
	{
		id: "APR-2026-0042",
		entityType: "Quote",
		entityId: "QT-2026-0019",
		requestedBy: "Onyx AI Assistant (Service Agent)",
		actorType: "Agent",
		title: "Demande de Remise Exceptionnelle de 25% (Devis Dune 3)",
		reason: "Fidélisation grand compte pour tournage long métrage de 14 jours. Dépassement du seuil agent de 15%.",
		policy: "POL-PRICING-DISCOUNT-MAX",
		currentValue: "18 450 $ CAD (Remise standard 10%)",
		proposedValue: "15 375 $ CAD (Remise VIP 25%)",
		status: "En attente",
		createdAt: "Aujourd'hui à 09:42",
		impactLevel: "Moyen",
	},
	{
		id: "APR-2026-0043",
		entityType: "Contract",
		entityId: "CTR-2026-0088",
		requestedBy: "Onyx AI Assistant (Service Agent)",
		actorType: "Agent",
		title: "Dérogation de Sortie avec Caution Partielle (HBO Studios)",
		reason: "Urgence plateau : tournage démarre à 06h00 demain. Virement séquestre en transit (35 000 $).",
		policy: "POL-SECURITY-DEPOSIT-MANDATORY",
		currentValue: "Blocage de sortie contractuel (PRD-CLI)",
		proposedValue: "Autorisation de scan check-out anticipé sous garantie signée du Directeur de Production",
		status: "En attente",
		createdAt: "Aujourd'hui à 10:15",
		impactLevel: "Élevé",
	},
]);

// Journal d'Audit Immuable (PRD-ARCH Rule #4)
const AUDIT_EVENTS = ref([
	{
		id: "AUD-89102",
		timestamp: "2026-09-17 10:25:12",
		actor: "Jean D. (Superviseur Comptable)",
		actorType: "Humain",
		action: "approval",
		entity: "Quote QT-2026-0018",
		requestId: "req_f81902cba",
		policy: "POL-PRICING-APPROVAL",
		diffSummary: "Remise commerciale 12% validée",
		details: {
			before: { discount_pct: 0, total: 12000 },
			after: { discount_pct: 12, total: 10560 },
		},
	},
	{
		id: "AUD-89101",
		timestamp: "2026-09-17 10:18:44",
		actor: "Onyx AI Agent",
		actorType: "Agent",
		action: "create",
		entity: "Approval Request APR-2026-0043",
		requestId: "req_c91019efa",
		policy: "POL-AGENT-AUTONOMY-SUPERVISED",
		diffSummary: "Soumission de demande de dérogation caution",
		details: {
			before: null,
			after: { status: "Pending", threshold_exceeded: true },
		},
	},
	{
		id: "AUD-89100",
		timestamp: "2026-09-17 09:55:03",
		actor: "Sophie M. (Magasinière Atelier)",
		actorType: "Humain",
		action: "checkout",
		entity: "Serial SN-ALX-001",
		requestId: "req_a11409cca",
		policy: "POL-INVENTORY-SCAN-DISPATCH",
		diffSummary: "Scan bon de sortie #MOCK-DOC-1",
		details: {
			before: { status: "Réservé", location: "Zone A" },
			after: { status: "En tournage", location: "Dune 3" },
		},
	},
	{
		id: "AUD-89099",
		timestamp: "2026-09-17 09:30:18",
		actor: "Onyx AI Agent",
		actorType: "Agent",
		action: "update",
		entity: "Rental Profile ARRI-ALX35",
		requestId: "req_b72288001",
		policy: "POL-TELEMETRY-UPDATE",
		diffSummary: "Mise à jour compteur horaire capteur (412h)",
		details: {
			before: { total_hours: 400 },
			after: { total_hours: 412 },
		},
	},
]);

const selectedEvent = ref(null);
const isDrawerOpen = ref(false);

function approveRequest(req) {
	req.status = "Approuvée";
	toast.success(`✓ Demande ${req.id} approuvée par l'opérateur humain.`);
	// Simulation ajout au journal d'audit immuable
	AUDIT_EVENTS.value.unshift({
		id: `AUD-${Math.floor(Math.random() * 10000 + 90000)}`,
		timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
		actor: "Opérateur Superviseur (Vous)",
		actorType: "Humain",
		action: "approval",
		entity: `${req.entityType} ${req.entityId}`,
		requestId: `req_${Math.random().toString(36).substring(2, 9)}`,
		policy: req.policy,
		diffSummary: `Approbation manuelle de ${req.title}`,
		details: { before: { status: "Pending" }, after: { status: "Approved" } },
	});
}

function rejectRequest(req) {
	req.status = "Rejetée";
	toast.info(`Demande ${req.id} rejetée avec notification à l'agent.`);
}

function openEventDetail(evt) {
	selectedEvent.value = evt;
	isDrawerOpen.value = true;
}
</script>

<template>
	<div class="cortex-app cx-app">
		<CortexToast />
		<CortexPageHeader
			title="Supervision IA & Approbations"
			subtitle="Gouvernance Human-in-the-loop (Règle #5), file des décisions sensibles et journal d'audit immuable (Règle #4)."
		/>

		<!-- Grille KPI -->
		<div class="cx-kpi-grid" style="margin-bottom: var(--space-4)">
			<CortexKpiCard
				title="Demandes en Attente"
				:value="APPROVAL_REQUESTS.filter(r => r.status === 'En attente').length + ' requêtes'"
				:trend="-25.0"
				badge="Action Requise"
				:sparkline="[5, 4, 4, 3, 2, 2]"
			/>
			<CortexKpiCard
				title="Taux d'Accord Humain"
				value="91.4%"
				:trend="3.2"
				badge="Conformité"
				:sparkline="[85, 87, 88, 89, 90, 91]"
			/>
			<CortexKpiCard
				title="Événements Audit (24h)"
				value="428 mutations"
				:trend="14.8"
				badge="Append-Only"
				:sparkline="[350, 380, 390, 410, 420, 428]"
			/>
			<CortexKpiCard
				title="Multi-Tenant Scoping"
				value="100% Isolé"
				:trend="0"
				badge="X-Company-ID"
				:sparkline="[100, 100, 100, 100, 100, 100]"
			/>
		</div>

		<!-- Onglets Principaux -->
		<div class="cx-tabs-bar cx-surface">
			<button
				class="cx-tab-btn"
				:class="{ 'is-active': activeTab === 'approvals' }"
				@click="activeTab = 'approvals'"
			>
				<span class="cx-icon-sm" v-html="ICONS.alert"></span>
				<span>File d'Approbation Humaine ({{ APPROVAL_REQUESTS.filter(r => r.status === 'En attente').length }})</span>
			</button>
			<button
				class="cx-tab-btn"
				:class="{ 'is-active': activeTab === 'audit' }"
				@click="activeTab = 'audit'"
			>
				<span class="cx-icon-sm" v-html="ICONS.shield"></span>
				<span>Journal d'Audit Immuable (Audit Event)</span>
			</button>
		</div>

		<!-- ONGLET 1 : File des Approbations Humaines -->
		<div v-if="activeTab === 'approvals'" class="cx-approvals-flow">
			<div
				v-for="req in APPROVAL_REQUESTS"
				:key="req.id"
				class="cx-approval-card cx-surface"
				:class="{ 'is-resolved': req.status !== 'En attente' }"
			>
				<div class="cx-card-top">
					<div class="cx-card-badges">
						<span class="cx-badge cx-badge-neutral">{{ req.id }}</span>
						<span class="cx-badge cx-badge-info">{{ req.entityType }} : {{ req.entityId }}</span>
						<span
							class="cx-badge"
							:class="req.impactLevel === 'Élevé' ? 'cx-badge-danger' : 'cx-badge-warning'"
						>
							Impact {{ req.impactLevel }}
						</span>
						<span class="cx-badge cx-badge-success">Policy : {{ req.policy }}</span>
					</div>
					<span class="cx-text-meta">{{ req.createdAt }}</span>
				</div>

				<h3 class="cx-card-title">{{ req.title }}</h3>
				<p class="cx-card-reason">
					<strong>Justification IA (Onyx) :</strong> {{ req.reason }}
				</p>

				<!-- Comparateur Visuel Diff -->
				<div class="cx-diff-box">
					<div class="cx-diff-col before">
						<span class="cx-diff-label">État Actuel (Standard)</span>
						<div class="cx-diff-value">{{ req.currentValue }}</div>
					</div>
					<div class="cx-diff-arrow">➔</div>
					<div class="cx-diff-col after">
						<span class="cx-diff-label">Proposition Soumise par l'Agent</span>
						<div class="cx-diff-value">{{ req.proposedValue }}</div>
					</div>
				</div>

				<!-- Actions de Décision Humaine -->
				<div class="cx-card-footer">
					<div class="cx-rule-notice">
						<span class="cx-icon-sm cx-emerald" v-html="ICONS.shield"></span>
						<span>Règle #5 : Un agent ne peut jamais approuver sa propre demande. Décision humaine requise.</span>
					</div>

					<div v-if="req.status === 'En attente'" class="cx-action-buttons">
						<button class="cx-btn cx-btn-ghost" @click="rejectRequest(req)">
							Rejeter avec motif
						</button>
						<button class="cx-btn cx-btn-primary" @click="approveRequest(req)">
							✓ Approuver la demande
						</button>
					</div>

					<div v-else class="cx-status-tag">
						<span
							class="cx-badge"
							:class="req.status === 'Approuvée' ? 'cx-badge-success' : 'cx-badge-danger'"
						>
							Statut : {{ req.status }}
						</span>
					</div>
				</div>
			</div>
		</div>

		<!-- ONGLET 2 : Journal d'Audit Immuable -->
		<div v-else class="cx-surface cx-table-card">
			<table class="cx-table">
				<thead>
					<tr>
						<th>ID Événement</th>
						<th>Horodatage UTC</th>
						<th>Acteur &amp; Contexte</th>
						<th>Action</th>
						<th>Entité Ciblée</th>
						<th>Politique de Sécurité</th>
						<th>Request ID</th>
						<th style="text-align: right">Détails</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="evt in AUDIT_EVENTS"
						:key="evt.id"
						class="cx-clickable-row"
						@click="openEventDetail(evt)"
					>
						<td><code>{{ evt.id }}</code></td>
						<td style="font-family: var(--font-mono); font-size: 11px">{{ evt.timestamp }}</td>
						<td>
							<div style="font-weight: 500">{{ evt.actor }}</div>
							<span
								class="cx-badge"
								:class="evt.actorType === 'Agent' ? 'cx-badge-info' : 'cx-badge-neutral'"
							>
								{{ evt.actorType }}
							</span>
						</td>
						<td>
							<span class="cx-badge cx-badge-neutral">{{ evt.action }}</span>
						</td>
						<td><strong>{{ evt.entity }}</strong></td>
						<td><code>{{ evt.policy }}</code></td>
						<td><code>{{ evt.requestId }}</code></td>
						<td style="text-align: right">
							<button class="cx-btn cx-btn-ghost" @click.stop="openEventDetail(evt)">
								Diff ↗
							</button>
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<!-- Slide-Over Drawer Inspection Audit Diff -->
		<CortexSlideOver
			:open="isDrawerOpen"
			:title="selectedEvent ? 'Audit Event ' + selectedEvent.id : ''"
			:subtitle="selectedEvent ? selectedEvent.entity + ' • ' + selectedEvent.timestamp : ''"
			width="580px"
			@close="isDrawerOpen = false"
		>
			<template v-if="selectedEvent">
				<div class="cx-section-block">
					<span class="cx-badge cx-badge-success" style="margin-bottom: var(--space-2)">
						Immuable (before_save / on_trash levés)
					</span>
					<p class="cx-meta-p">
						<strong>Acteur :</strong> {{ selectedEvent.actor }} ({{ selectedEvent.actorType }})<br />
						<strong>Politique :</strong> <code>{{ selectedEvent.policy }}</code><br />
						<strong>Request ID :</strong> <code>{{ selectedEvent.requestId }}</code><br />
						<strong>Synthèse :</strong> {{ selectedEvent.diffSummary }}
					</p>
				</div>

				<div class="cx-section-block">
					<h4 class="cx-section-title">Payload d'État Avant / Après (JSON Typé)</h4>
					<pre class="cx-json-pre">{{ JSON.stringify(selectedEvent.details, null, 2) }}</pre>
				</div>
			</template>

			<template #footer>
				<button class="cx-btn cx-btn-ghost" @click="isDrawerOpen = false">Fermer</button>
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

.cx-tabs-bar {
	display: flex;
	gap: var(--space-2);
	padding: var(--space-2);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	margin-bottom: var(--space-4);
}

.cx-tab-btn {
	display: inline-flex;
	align-items: center;
	gap: var(--space-2);
	padding: 8px var(--space-4);
	border-radius: var(--radius-md);
	border: 1px solid transparent;
	background: transparent;
	font-size: 13px;
	font-weight: 500;
	color: var(--cortex-text-muted);
	cursor: pointer;
	transition: all 0.1s ease;
}

.cx-tab-btn:hover {
	color: var(--cortex-text-primary);
	background: var(--cortex-surface-muted);
}

.cx-tab-btn.is-active {
	background: var(--cortex-primary-50);
	border-color: var(--cortex-primary-200);
	color: var(--cortex-primary-700);
}

.cx-approvals-flow {
	display: flex;
	flex-direction: column;
	gap: var(--space-4);
}

.cx-approval-card {
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	padding: var(--space-4);
	transition: opacity 0.15s ease;
}
.cx-approval-card.is-resolved {
	opacity: 0.7;
}

.cx-card-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: var(--space-2);
}

.cx-card-badges {
	display: flex;
	gap: var(--space-2);
	flex-wrap: wrap;
}

.cx-card-title {
	font-size: 14.5px;
	font-weight: 600;
	color: var(--cortex-text-primary);
	margin: var(--space-2) 0;
}

.cx-card-reason {
	font-size: 12.5px;
	color: var(--cortex-text-primary);
	background: var(--cortex-surface-muted);
	padding: var(--space-3);
	border-radius: var(--radius-md);
	margin: 0 0 var(--space-3);
	line-height: 1.4;
}

.cx-diff-box {
	display: grid;
	grid-template-columns: 1fr auto 1fr;
	gap: var(--space-3);
	align-items: center;
	background: var(--cortex-surface-muted);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-3);
	margin-bottom: var(--space-3);
}

.cx-diff-col {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.cx-diff-label {
	font-size: 10.5px;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--cortex-text-muted);
	font-weight: 600;
}

.cx-diff-value {
	font-size: 13px;
	font-weight: 600;
	color: var(--cortex-text-primary);
}

.cx-diff-col.after .cx-diff-value {
	color: var(--cortex-primary-700);
}

.cx-diff-arrow {
	font-size: 16px;
	color: var(--cortex-text-muted);
}

.cx-card-footer {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding-top: var(--space-3);
	border-top: 1px solid var(--cortex-border);
	flex-wrap: wrap;
	gap: var(--space-3);
}

.cx-rule-notice {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 11.5px;
	color: var(--cortex-text-muted);
}

.cx-action-buttons {
	display: flex;
	gap: var(--space-2);
}

.cx-table-card {
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	overflow: hidden;
}

.cx-clickable-row {
	cursor: pointer;
}
.cx-clickable-row:hover {
	background: var(--cortex-surface-muted);
}

.cx-meta-p {
	font-size: 12.5px;
	line-height: 1.6;
	color: var(--cortex-text-primary);
}

.cx-json-pre {
	background: var(--cortex-surface-muted);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-3);
	font-family: var(--font-mono);
	font-size: 11.5px;
	overflow-x: auto;
}

.cx-section-block {
	margin-bottom: var(--space-4);
}

.cx-section-title {
	font-size: 13px;
	font-weight: 600;
	color: var(--cortex-text-primary);
	margin: 0 0 var(--space-2);
}

.cx-emerald {
	color: var(--cortex-primary-600);
}

@media (max-width: 1024px) {
	.cx-kpi-grid {
		grid-template-columns: repeat(2, 1fr);
	}
	.cx-diff-box {
		grid-template-columns: 1fr;
	}
}
@media (max-width: 640px) {
	.cx-kpi-grid {
		grid-template-columns: 1fr;
	}
}
</style>
