<script setup>
import { ref } from "vue";

const props = defineProps({
	block: { type: Object, required: true }, // {title, summary, impact, action, draft_id, requires_approval, customer_id, items}
});

const emit = defineEmits(["continue"]);

const creating = ref(false);
const createdId = ref(null);
const errorMessage = ref("");

function onContinue() {
	emit("continue", props.block.title);
}

function openTransaction() {
	if (createdId.value) {
		frappe.set_route("Form", "Cortex Rental Transaction", createdId.value);
	}
}

async function createQuote() {
	creating.value = true;
	errorMessage.value = "";
	try {
		// Résolution d'un client par défaut si non spécifié
		let customerId = props.block.customer_id;
		if (!customerId) {
			const customers = await new Promise((resolve) => {
				frappe.call({
					method: "cortex_rental.api.v1.rentals.search_rental_customers",
					callback: (r) => resolve(r.message?.items || []),
				});
			});
			customerId = customers[0]?.id;
		}

		if (!customerId) {
			throw new Error("Aucun client trouvé dans le système pour associer la soumission.");
		}

		// Dates par défaut : demain à +3 jours
		const start = new Date();
		start.setDate(start.getDate() + 1);
		start.setHours(9, 0, 0, 0);
		const end = new Date(start);
		end.setDate(end.getDate() + 3);
		end.setHours(18, 0, 0, 0);

		const formatDate = (d) => d.toISOString().slice(0, 19).replace("T", " ");

		// Équipements de la proposition ou du catalogue
		let items = props.block.items || [];
		if (!items.length) {
			const catalog = await new Promise((resolve) => {
				frappe.call({
					method: "cortex_rental.api.v1.rentals.search_rental_catalog",
					callback: (r) => resolve(r.message?.items || []),
				});
			});
			items = catalog.slice(0, 2).map((it) => ({
				item_code: it.item_code,
				quantity: 1,
			}));
		}

		if (!items.length) {
			throw new Error("Aucun équipement disponible pour créer le devis.");
		}

		const response = await new Promise((resolve, reject) => {
			frappe.call({
				method: "cortex_rental.api.v1.rentals.create_quote_draft",
				type: "POST",
				args: {
					customer_id: customerId,
					starts_at: formatDate(start),
					ends_at: formatDate(end),
					items: JSON.stringify(items),
					notes: "Créé automatiquement via le Copilote Cortex.",
				},
				callback: (r) => resolve(r.message || {}),
				error: (r) => reject(new Error(r.message || "Erreur de validation lors de la création de la soumission.")),
			});
		});

		const newName = response.name || response.data || response;
		createdId.value = typeof newName === "string" ? newName : "Enregistré";
	} catch (err) {
		errorMessage.value = err.message || "Impossible de créer la soumission.";
	} finally {
		creating.value = false;
	}
}
</script>

<template>
	<div class="cp-block cp-block-proposal">
		<div class="cp-block-head">
			<span class="cx-title-card">{{ block.title }}</span>
			<span v-if="block.requires_approval" class="cx-badge cp-approval-flag">approbation requise</span>
		</div>
		<p class="cx-text-body">{{ block.summary }}</p>
		<ul v-if="block.impact && block.impact.length" class="cp-impact-list">
			<li v-for="(line, i) in block.impact" :key="i" class="cx-text-meta">{{ line }}</li>
		</ul>

		<!-- État SUCCÈS : Transaction créée -->
		<div v-if="createdId" class="cp-proposal-success">
			<div class="cp-success-badge">
				<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
					<polyline points="20 6 9 17 4 12"/>
				</svg>
				<span>Soumission créée : <strong>{{ createdId }}</strong></span>
			</div>
			<button type="button" class="cx-btn cx-btn-primary cp-action-btn" @click="openTransaction">
				Ouvrir la transaction dans ERPNext ↗
			</button>
		</div>

		<!-- État INITIAL : Actions de création ou de continuation -->
		<div v-else class="cp-proposal-actions">
			<button
				type="button"
				class="cx-btn cx-btn-primary cp-action-btn"
				:disabled="creating"
				@click="createQuote"
			>
				<span v-if="creating">Création en cours…</span>
				<span v-else>Créer la soumission dans ERPNext</span>
			</button>
			<button
				type="button"
				class="cx-btn cx-btn-secondary cp-action-btn-secondary"
				:disabled="creating"
				@click="onContinue"
			>
				Poursuivre la conversation
			</button>
		</div>

		<p v-if="errorMessage" class="cp-proposal-error">{{ errorMessage }}</p>
	</div>
</template>

<style scoped>
.cp-block-proposal {
	background: var(--cortex-primary-50, #f0fdf4);
	border: 1px solid var(--cortex-primary-100, #bbf7d0);
	border-radius: var(--radius-md, 8px);
	padding: var(--space-3, 12px);
}

.cp-block-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-2, 8px);
	margin-bottom: var(--space-2, 8px);
}

.cx-title-card {
	font-size: 13px;
	font-weight: 600;
	color: #0f172a;
}

.cx-text-body {
	font-size: 13px;
	line-height: 1.45;
	color: #334155;
	margin: 0 0 8px;
}

.cp-approval-flag {
	background: var(--cortex-warning-50, #fffbeb);
	color: var(--cortex-warning-700, #b45309);
	border: 1px solid var(--cortex-warning-500, #f59e0b);
	font-size: 11px;
	padding: 2px 6px;
	border-radius: 4px;
	font-weight: 500;
}

.cp-impact-list {
	margin: 6px 0 12px;
	padding-left: 18px;
	list-style-type: disc;
}

.cx-text-meta {
	font-size: 12px;
	color: #64748b;
	line-height: 1.4;
}

.cp-proposal-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-top: 8px;
}

.cp-action-btn {
	background: #047857;
	color: #ffffff;
	border: none;
	border-radius: 6px;
	padding: 6px 12px;
	font-size: 12.5px;
	font-weight: 500;
	cursor: pointer;
	transition: background 0.15s;
}

.cp-action-btn:hover:not(:disabled) {
	background: #065f46;
}

.cp-action-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

.cp-action-btn-secondary {
	background: #ffffff;
	color: #475569;
	border: 1px solid #cbd5e1;
	border-radius: 6px;
	padding: 6px 12px;
	font-size: 12.5px;
	font-weight: 500;
	cursor: pointer;
	transition: background 0.15s, border-color 0.15s;
}

.cp-action-btn-secondary:hover:not(:disabled) {
	background: #f8fafc;
	border-color: #94a3b8;
}

.cp-proposal-success {
	display: flex;
	flex-direction: column;
	gap: 8px;
	margin-top: 8px;
}

.cp-success-badge {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	color: #065f46;
	background: #d1fae5;
	border-radius: 6px;
	padding: 6px 10px;
	font-size: 12.5px;
}

.cp-proposal-error {
	margin: 8px 0 0;
	font-size: 12px;
	color: #dc2626;
}
</style>
