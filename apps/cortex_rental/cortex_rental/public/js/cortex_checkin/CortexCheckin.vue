<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import CortexPageHeader from "../cortex_shared/CortexPageHeader.vue";
import CortexStatusBadge from "../cortex_shared/CortexStatusBadge.vue";
import CortexLoadingState from "../cortex_shared/CortexLoadingState.vue";
import CortexErrorState from "../cortex_shared/CortexErrorState.vue";
import CortexEmptyState from "../cortex_shared/CortexEmptyState.vue";
import { formatCurrency } from "../cortex_shared/formatters.js";
import { fmtDateTime } from "../cortex_shared/dateUtils.js";
import CortexToast from "../cortex_shared/CortexToast.vue";
import { toast } from "../cortex_shared/toastBus.js";

// ---------------------------------------------------------------------
// State & Navigation
// ---------------------------------------------------------------------
const currentStep = ref(1); // 1: Live Scan, 2: Diagnostics & Bris, 3: Bilan & Clôture
const scanInput = ref("");
const scanInputRef = ref(null);
const scanFlash = ref(""); // "success" | "warning" | "error"
const scanFeedbackMsg = ref("");

// Active transactions list (Checked Out)
const activeTransactions = ref([]);
const transactionsLoading = ref(false);
const transactionsError = ref("");
const selectedTransaction = ref(null);
const transactionSearch = ref("");

// Checked-in items working state:
// Array of { transaction_item, item_code, item_name, serial_no, expected_qty, returned_qty, condition, disposition, damage_severity, damage_type, estimated_repair_cost, notes, is_scanned }
const returnItems = ref([]);

// Finalization & Submission state
const finalizeMode = ref("auto"); // "auto" | "partial" | "full" | "settle_with_loss"
const checkinNotes = ref("");
const submitting = ref(false);
const submitError = ref("");
const completedReceipt = ref(null);

// ---------------------------------------------------------------------
// Sound Cues (Web Audio API)
// ---------------------------------------------------------------------
function playAudioCue(type) {
	try {
		const AudioContext = window.AudioContext || window.webkitAudioContext;
		if (!AudioContext) return;
		const ctx = new AudioContext();
		const osc = ctx.createOscillator();
		const gain = ctx.createGain();
		osc.connect(gain);
		gain.connect(ctx.destination);

		if (type === "success") {
			osc.type = "sine";
			osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
			osc.frequency.setValueAtTime(880, ctx.currentTime + 0.08); // A5
			gain.gain.setValueAtTime(0.12, ctx.currentTime);
			gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.22);
			osc.start(ctx.currentTime);
			osc.stop(ctx.currentTime + 0.22);
		} else if (type === "warning") {
			osc.type = "triangle";
			osc.frequency.setValueAtTime(440, ctx.currentTime);
			osc.frequency.setValueAtTime(349.23, ctx.currentTime + 0.1);
			gain.gain.setValueAtTime(0.15, ctx.currentTime);
			gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.28);
			osc.start(ctx.currentTime);
			osc.stop(ctx.currentTime + 0.28);
		} else if (type === "error") {
			osc.type = "sawtooth";
			osc.frequency.setValueAtTime(220, ctx.currentTime);
			gain.gain.setValueAtTime(0.15, ctx.currentTime);
			gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
			osc.start(ctx.currentTime);
			osc.stop(ctx.currentTime + 0.25);
		}
	} catch (e) {
		// Silent fallback if audio context is blocked
	}
}

// ---------------------------------------------------------------------
// Lifecycle & Data Fetching
// ---------------------------------------------------------------------
onMounted(() => {
	loadActiveTransactions();
	focusScanner();
});

function focusScanner() {
	nextTick(() => {
		if (scanInputRef.value) {
			scanInputRef.value.focus();
		}
	});
}

function loadActiveTransactions(preselectId = null) {
	transactionsLoading.value = true;
	transactionsError.value = "";

	frappe.call({
		method: "cortex_rental.api.v1.checkin.get_active_transactions",
		type: "GET",
		callback(r) {
			transactionsLoading.value = false;
			activeTransactions.value = (r.message && r.message.data) || [];

			// Check if preselection requested via route_options or argument
			let targetId = preselectId;
			if (!targetId && frappe.route_options && frappe.route_options.transaction) {
				targetId = frappe.route_options.transaction;
				frappe.route_options = null;
			}

			if (targetId) {
				const match = activeTransactions.value.find((t) => t.name === targetId);
				if (match) {
					selectTransaction(match);
				}
			}
		},
		error(err) {
			transactionsLoading.value = false;
			transactionsError.value = (err && err.message) || "Impossible de charger les transactions en cours.";
		},
	});
}

function selectTransaction(txn) {
	selectedTransaction.value = txn;
	currentStep.value = 1;
	submitError.value = "";
	completedReceipt.value = null;

	// Populate working return items
	returnItems.value = (txn.items || []).map((item) => {
		const remaining = Math.max(0, (item.qty || 1.0) - (item.returned_qty || 0.0));
		return {
			transaction_item: item.name,
			item_code: item.item_code,
			item_name: item.item_name || item.item_code,
			serial_no: item.serial_no || null,
			serial_status: item.serial_status || "Active",
			qty: item.qty || 1.0,
			already_returned: item.returned_qty || 0.0,
			expected_qty: remaining,
			returned_qty: 0.0,
			condition: "Good",
			disposition: "Return to Stock",
			damage_severity: "None",
			damage_type: "None",
			estimated_repair_cost: 0.0,
			notes: "",
			is_scanned: false,
		};
	});

	focusScanner();
}

function resetSelection() {
	selectedTransaction.value = null;
	returnItems.value = [];
	completedReceipt.value = null;
	currentStep.value = 1;
	loadActiveTransactions();
}

// ---------------------------------------------------------------------
// Scanner Logic (Hardware Barcode Gun / Keyboard Input)
// ---------------------------------------------------------------------
function handleScanSubmit() {
	const code = (scanInput.value || "").trim();
	if (!code) return;
	scanInput.value = "";

	// 1. If no transaction is selected, try lookup on server or local list
	if (!selectedTransaction.value) {
		resolveGlobalScan(code);
		return;
	}

	// 2. Transaction is active: match locally first for zero-latency response
	const matchedBySerial = returnItems.value.find((i) => i.serial_no && i.serial_no.toLowerCase() === code.toLowerCase());

	if (matchedBySerial) {
		markSerialReturned(matchedBySerial);
		triggerScanFeedback("success", `✓ Numéro de série ${matchedBySerial.serial_no} réceptionné.`);
		return;
	}

	const matchedByItemCode = returnItems.value.find((i) => i.item_code.toLowerCase() === code.toLowerCase() && !i.serial_no);

	if (matchedByItemCode) {
		incrementBulkReturned(matchedByItemCode, 1);
		triggerScanFeedback("success", `✓ Code article ${matchedByItemCode.item_code} scanné (+1).`);
		return;
	}

	// 3. Fallback to server lookup if not matched in active transaction
	resolveGlobalScan(code);
}

function resolveGlobalScan(code) {
	frappe.call({
		method: "cortex_rental.api.v1.checkin.lookup_scan",
		type: "GET",
		args: { scan_code: code },
		callback(r) {
			const data = (r.message && r.message.data) || {};
			if (data.type === "transaction" && data.transaction) {
				const match = activeTransactions.value.find((t) => t.name === data.transaction.name);
				if (match) {
					selectTransaction(match);
					triggerScanFeedback("success", `✓ Dossier ${match.name} chargé avec succès.`);
				} else {
					loadActiveTransactions(data.transaction.name);
					triggerScanFeedback("success", `✓ Dossier ${data.transaction.name} chargé.`);
				}
			} else if (data.type === "serial" && data.transaction) {
				const match = activeTransactions.value.find((t) => t.name === data.transaction.name);
				if (match) {
					selectTransaction(match);
					nextTick(() => {
						const itemRow = returnItems.value.find((i) => i.serial_no === data.serial_no);
						if (itemRow) markSerialReturned(itemRow);
					});
					triggerScanFeedback("success", `✓ Dossier ${data.transaction.name} chargé & Serial No ${data.serial_no} scanné.`);
				} else {
					loadActiveTransactions(data.transaction.name);
				}
			} else {
				triggerScanFeedback("error", `⚠️ Code "${code}" non reconnu sur les locations en cours.`);
			}
		},
		error() {
			triggerScanFeedback("error", `Erreur lors de la recherche du code "${code}".`);
		},
	});
}

function triggerScanFeedback(type, message) {
	scanFlash.value = type;
	scanFeedbackMsg.value = message;
	playAudioCue(type);
	if (type === "success") {
		toast.success(message);
	} else if (type === "warning") {
		toast.warning(message);
	} else if (type === "error") {
		toast.error(message);
	}
	setTimeout(() => {
		if (scanFlash.value === type) scanFlash.value = "";
	}, 1200);
}

// ---------------------------------------------------------------------
// Item Manipulation Helpers
// ---------------------------------------------------------------------
function markSerialReturned(item) {
	if (item.returned_qty <= 0) {
		item.returned_qty = 1.0;
		item.is_scanned = true;
		if (item.condition === "Good") {
			item.disposition = "Return to Stock";
		}
	} else {
		// Toggle off if re-clicked manually
		item.returned_qty = 0.0;
		item.is_scanned = false;
	}
}

function incrementBulkReturned(item, delta) {
	const current = item.returned_qty || 0;
	const max = item.expected_qty || item.qty;
	const updated = Math.max(0, Math.min(max, current + delta));
	item.returned_qty = updated;
	item.is_scanned = updated > 0;
}

function returnAllBulk(item) {
	item.returned_qty = item.expected_qty || item.qty;
	item.is_scanned = true;
	triggerScanFeedback("success", `✓ Tous les exemplaires de ${item.item_name} cochés.`);
}

function returnAllGoodItems() {
	returnItems.value.forEach((item) => {
		if (item.condition === "Good") {
			item.returned_qty = item.expected_qty || item.qty;
			item.is_scanned = true;
			item.disposition = "Return to Stock";
		}
	});
	triggerScanFeedback("success", "✓ Tous les articles restants ont été marqués reçus en bon état.");
}

function flagItemForDamage(item) {
	item.condition = "Damaged";
	item.disposition = "Repair";
	if (item.damage_severity === "None") item.damage_severity = "Functional";
	if (item.returned_qty <= 0) item.returned_qty = item.serial_no ? 1.0 : 1.0;
	item.is_scanned = true;
	currentStep.value = 2; // Jump to diagnostic review
}

function flagItemForMissing(item) {
	item.condition = "Missing";
	item.disposition = "Missing";
	item.damage_severity = "Blocking";
	item.returned_qty = 0.0;
	item.is_scanned = true;
	currentStep.value = 2;
}

// ---------------------------------------------------------------------
// Computed Stats & Metrics
// ---------------------------------------------------------------------
const filteredTransactions = computed(() => {
	if (!transactionSearch.value.trim()) return activeTransactions.value;
	const q = transactionSearch.value.toLowerCase().trim();
	return activeTransactions.value.filter(
		(t) =>
			(t.name && t.name.toLowerCase().includes(q)) ||
			(t.customer && t.customer.toLowerCase().includes(q)) ||
			(t.customer_name && t.customer_name.toLowerCase().includes(q))
	);
});

const abnormalItems = computed(() => {
	return returnItems.value.filter((i) => i.condition === "Damaged" || i.condition === "Missing" || i.disposition !== "Return to Stock");
});

const totalExpectedQty = computed(() => {
	return returnItems.value.reduce((acc, i) => acc + (i.expected_qty || 0), 0);
});

const totalReturnedQty = computed(() => {
	return returnItems.value.reduce((acc, i) => acc + (i.returned_qty || 0), 0);
});

const totalGoodQty = computed(() => {
	return returnItems.value.filter((i) => i.condition === "Good").reduce((acc, i) => acc + (i.returned_qty || 0), 0);
});

const totalDamagedQty = computed(() => {
	return returnItems.value.filter((i) => i.condition === "Damaged").reduce((acc, i) => acc + (i.returned_qty || 0), 0);
});

const totalMissingQty = computed(() => {
	return returnItems.value.filter((i) => i.condition === "Missing").length;
});

const totalEstimatedRepairCost = computed(() => {
	return returnItems.value.reduce((acc, i) => acc + Number(i.estimated_repair_cost || 0), 0);
});

const isFullyRestituted = computed(() => {
	return returnItems.value.every((i) => (i.returned_qty || 0) >= (i.expected_qty || 1));
});

// ---------------------------------------------------------------------
// Final Submission
// ---------------------------------------------------------------------
function submitCheckin() {
	if (!selectedTransaction.value) return;

	// Build items payload
	const payloadItems = returnItems.value
		.filter((i) => (i.returned_qty || 0) > 0 || i.condition === "Missing")
		.map((i) => ({
			transaction_item: i.transaction_item,
			item_code: i.item_code,
			serial_no: i.serial_no,
			expected_qty: i.expected_qty,
			returned_qty: i.returned_qty,
			condition: i.condition,
			disposition: i.disposition,
			damage_severity: i.damage_severity,
			damage_type: i.damage_type,
			estimated_repair_cost: i.estimated_repair_cost,
			notes: i.notes,
		}));

	if (payloadItems.length === 0) {
		submitError.value = "Veuillez réceptionner au moins un article ou déclarer un manquant.";
		return;
	}

	submitting.value = true;
	submitError.value = "";

	const idempotencyKey = "chk-" + selectedTransaction.value.name + "-" + Date.now();

	frappe.call({
		method: "cortex_rental.api.v1.checkin.submit_checkin",
		type: "POST",
		headers: {
			"Idempotency-Key": idempotencyKey,
		},
		args: {
			transaction_id: selectedTransaction.value.name,
			items: JSON.stringify(payloadItems),
			finalize_mode: finalizeMode.value === "auto" ? (isFullyRestituted.value ? "full" : "partial") : finalizeMode.value,
			notes: checkinNotes.value,
		},
		callback(r) {
			submitting.value = false;
			const data = (r.message && r.message.data) || {};
			completedReceipt.value = {
				id: data.id || "CHK-COMPLETED",
				transaction: selectedTransaction.value.name,
				customer: selectedTransaction.value.customer_name || selectedTransaction.value.customer,
				date: new Date(),
				fully_returned: data.transaction_fully_returned,
				items: [...returnItems.value],
				repair_cost: totalEstimatedRepairCost.value,
				operator: frappe.session.user_fullname || frappe.session.user,
			};
			triggerScanFeedback("success", "✓ Réception enregistrée et auditée avec succès !");
		},
		error(err) {
			submitting.value = false;
			submitError.value = (err && err.message) || "Erreur lors de la validation du Check-In.";
			triggerScanFeedback("error", "Erreur lors de l'enregistrement.");
		},
	});
}

function printReceipt() {
	window.print();
}

function navigateToTransaction(name) {
	frappe.set_route("Form", "Cortex Rental Transaction", name);
}
</script>

<template>
	<div class="cx-checkin-app cortex-app">
		<!-- Global Toast Container -->
		<CortexToast />
		<!-- Top Page Header -->
		<CortexPageHeader
			title="Check-in Scanner & Réception"
			subtitle="Réception matérielle, diagnostic d'avarie, remise en stock et clôture de contrat."
		>
			<template #status>
				<CortexStatusBadge v-if="selectedTransaction" state="Checked Out" label="Sortie active" />
			</template>

			<template #secondary>
				<button v-if="selectedTransaction && !completedReceipt" class="cx-btn cx-btn-secondary" @click="resetSelection">
					← Changer de dossier
				</button>
				<button v-if="completedReceipt" class="cx-btn cx-btn-secondary" @click="printReceipt">
					🖨️ Imprimer le bon de retour
				</button>
			</template>

			<template #primary>
				<button
					v-if="selectedTransaction && !completedReceipt && currentStep === 1"
					class="cx-btn cx-btn-primary"
					@click="currentStep = abnormalItems.length > 0 ? 2 : 3"
				>
					{{ abnormalItems.length > 0 ? "Étape 2 : Revue des écarts (" + abnormalItems.length + ") →" : "Étape 3 : Bilan & Clôture →" }}
				</button>
				<button v-if="completedReceipt" class="cx-btn cx-btn-primary" @click="resetSelection">
					+ Nouveau Check-in
				</button>
			</template>
		</CortexPageHeader>

		<!-- ============================================================= -->
		<!-- SCREEN A : SELECTION DU DOSSIER SI AUCUN DOSSIER SELECTIONNE -->
		<!-- ============================================================= -->
		<div v-if="!selectedTransaction && !completedReceipt" class="cx-panel cx-transaction-picker-panel">
			<!-- Fast Global Scan Input -->
			<div class="cx-fast-scan-bar" :class="{ 'cx-scan-flash-success': scanFlash === 'success', 'cx-scan-flash-error': scanFlash === 'error' }">
				<span class="cx-scan-icon" aria-hidden="true">⚡</span>
				<input
					ref="scanInputRef"
					v-model="scanInput"
					type="text"
					class="cx-scan-input"
					placeholder="Scanner un équipement (Serial No / Code-barres) ou un Bon de livraison..."
					@keydown.enter.prevent="handleScanSubmit"
				/>
				<button class="cx-btn cx-btn-primary cx-btn-sm" @click="handleScanSubmit">
					Entrée / Scan
				</button>
			</div>

			<div v-if="scanFeedbackMsg" class="cx-scan-feedback" :class="`cx-feedback-${scanFlash}`">
				{{ scanFeedbackMsg }}
			</div>

			<!-- Active Checked-Out Transactions Table -->
			<div class="cx-section-header">
				<div>
					<h2 class="cx-title-section">Dossiers de location actuellement sortis</h2>
					<p class="cx-text-muted">Sélectionnez un contrat ou scannez directement un article pour ouvrir le dossier.</p>
				</div>
				<input
					v-model="transactionSearch"
					type="search"
					class="cx-search-input"
					placeholder="Filtrer par contrat ou client..."
				/>
			</div>

			<CortexLoadingState v-if="transactionsLoading" message="Chargement des contrats en cours de location..." />
			<CortexErrorState v-else-if="transactionsError" :message="transactionsError" @retry="loadActiveTransactions" />
			<CortexEmptyState
				v-else-if="filteredTransactions.length === 0"
				title="Aucune sortie active"
				description="Toutes les locations sont retournées ou aucune transaction n'est à l'état Checked Out."
			/>

			<div v-else class="cx-table-container">
				<table class="cx-table">
					<thead>
						<tr>
							<th scope="col">Dossier / Contrat</th>
							<th scope="col">Client</th>
							<th scope="col">Période de location</th>
							<th scope="col" class="cx-text-right">Articles</th>
							<th scope="col" class="cx-text-right">Restitution</th>
							<th scope="col" class="cx-text-center">Action</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="txn in filteredTransactions" :key="txn.name" class="cx-row-interactive" @click="selectTransaction(txn)">
							<td class="cx-font-semibold">{{ txn.name }}</td>
							<td>{{ txn.customer_name || txn.customer }}</td>
							<td class="cx-text-muted">
								{{ txn.starts_at ? fmtDateTime(txn.starts_at) : "—" }} →
								{{ txn.ends_at ? fmtDateTime(txn.ends_at) : "—" }}
							</td>
							<td class="cx-text-right">{{ txn.total_qty }} unités ({{ txn.total_lines }} lignes)</td>
							<td class="cx-text-right">
								<span
									class="cx-progress-pill"
									:class="{ 'cx-progress-done': txn.is_complete, 'cx-progress-pending': !txn.is_complete }"
								>
									{{ txn.returned_qty }} / {{ txn.total_qty }}
								</span>
							</td>
							<td class="cx-text-center">
								<button class="cx-btn cx-btn-secondary cx-btn-sm" @click.stop="selectTransaction(txn)">
									Ouvrir Check-in →
								</button>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>

		<!-- ============================================================= -->
		<!-- SCREEN B : DOSSIER ACTIF — WORKFLOW CONTINU 3 ÉTAPES          -->
		<!-- ============================================================= -->
		<div v-else-if="selectedTransaction && !completedReceipt" class="cx-workspace-flow">
			<!-- Stepper Navigation Bar -->
			<div class="cx-stepper">
				<button
					class="cx-step-tab"
					:class="{ 'cx-step-active': currentStep === 1, 'cx-step-done': currentStep > 1 }"
					@click="currentStep = 1"
				>
					<span class="cx-step-number">1</span>
					<span class="cx-step-label">Live Scan & Colisage</span>
				</button>
				<div class="cx-step-divider" />
				<button
					class="cx-step-tab"
					:class="{ 'cx-step-active': currentStep === 2, 'cx-step-done': currentStep > 2, 'cx-step-alert': abnormalItems.length > 0 }"
					@click="currentStep = 2"
				>
					<span class="cx-step-number">2</span>
					<span class="cx-step-label">
						Diagnostic & Bris
						<span v-if="abnormalItems.length > 0" class="cx-badge-count">{{ abnormalItems.length }}</span>
					</span>
				</button>
				<div class="cx-step-divider" />
				<button
					class="cx-step-tab"
					:class="{ 'cx-step-active': currentStep === 3 }"
					@click="currentStep = 3"
				>
					<span class="cx-step-number">3</span>
					<span class="cx-step-label">Bilan & Clôture</span>
				</button>
			</div>

			<!-- Summary Card of Selected Transaction -->
			<div class="cx-txn-summary-banner">
				<div class="cx-summary-meta">
					<span class="cx-summary-id">{{ selectedTransaction.name }}</span>
					<span class="cx-summary-client">👤 {{ selectedTransaction.customer_name || selectedTransaction.customer }}</span>
					<span class="cx-summary-dates">📅 Retour prévu : {{ selectedTransaction.ends_at ? fmtDateTime(selectedTransaction.ends_at) : "Non spécifié" }}</span>
				</div>
				<div class="cx-summary-stats">
					<span class="cx-stat-pill">
						Reçus : <strong>{{ totalReturnedQty }} / {{ totalExpectedQty }}</strong>
					</span>
					<span v-if="totalDamagedQty > 0" class="cx-stat-pill cx-pill-warning">
						⚠️ Bris : <strong>{{ totalDamagedQty }}</strong>
					</span>
					<span v-if="totalMissingQty > 0" class="cx-stat-pill cx-pill-danger">
						❌ Manquants : <strong>{{ totalMissingQty }}</strong>
					</span>
				</div>
			</div>

			<!-- ------------------------------------------------------------- -->
			<!-- STEP 1 : LIVE SCAN & COLISAGE                                 -->
			<!-- ------------------------------------------------------------- -->
			<section v-if="currentStep === 1" class="cx-step-section">
				<!-- Fast Scan Bar -->
				<div class="cx-fast-scan-bar" :class="{ 'cx-scan-flash-success': scanFlash === 'success', 'cx-scan-flash-error': scanFlash === 'error' }">
					<span class="cx-scan-icon">⚡</span>
					<input
						ref="scanInputRef"
						v-model="scanInput"
						type="text"
						class="cx-scan-input"
						placeholder="Scanner un numéro de série (ex: CAM-SN-01) ou code-barres accessoire..."
						@keydown.enter.prevent="handleScanSubmit"
					/>
					<button class="cx-btn cx-btn-primary cx-btn-sm" @click="handleScanSubmit">
						Valider Scan
					</button>
				</div>

				<div v-if="scanFeedbackMsg" class="cx-scan-feedback" :class="`cx-feedback-${scanFlash}`">
					{{ scanFeedbackMsg }}
				</div>

				<!-- Quick Action Toolbar -->
				<div class="cx-scan-toolbar">
					<span class="cx-text-muted">Tableau de réception en direct :</span>
					<div class="cx-flex cx-gap-2">
						<button class="cx-btn cx-btn-secondary cx-btn-sm" @click="returnAllGoodItems">
							✓ Tout réceptionner en bon état
						</button>
					</div>
				</div>

				<!-- Scan Table -->
				<div class="cx-table-container">
					<table class="cx-table">
						<thead>
							<tr>
								<th scope="col" style="width: 48px">État</th>
								<th scope="col">Article & Spécifications</th>
								<th scope="col">Numéro de série</th>
								<th scope="col" class="cx-text-center" style="width: 140px">Quantité Restituée</th>
								<th scope="col">Condition & Diagnostic</th>
								<th scope="col" class="cx-text-right">Actions rapides</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="item in returnItems"
								:key="item.transaction_item"
								:class="{
									'cx-row-scanned': item.returned_qty >= item.expected_qty && item.condition === 'Good',
									'cx-row-damaged': item.condition === 'Damaged',
									'cx-row-missing': item.condition === 'Missing',
								}"
							>
								<!-- Status Check Icon -->
								<td class="cx-text-center">
									<span v-if="item.condition === 'Good' && item.returned_qty >= item.expected_qty" class="cx-badge-icon cx-icon-success" title="Reçu sain">✓</span>
									<span v-else-if="item.condition === 'Damaged'" class="cx-badge-icon cx-icon-warning" title="Endommagé">⚠️</span>
									<span v-else-if="item.condition === 'Missing'" class="cx-badge-icon cx-icon-danger" title="Manquant">❌</span>
									<span v-else class="cx-badge-icon cx-icon-pending" title="En attente de scan">⏳</span>
								</td>

								<!-- Item Name & Code -->
								<td>
									<div class="cx-item-title">{{ item.item_name }}</div>
									<div class="cx-item-code">{{ item.item_code }}</div>
								</td>

								<!-- Serial No -->
								<td>
									<span v-if="item.serial_no" class="cx-serial-tag">
										🏷️ {{ item.serial_no }}
									</span>
									<span v-else class="cx-text-muted">Article en vrac / Non-sérialisé</span>
								</td>

								<!-- Returned Qty Controls -->
								<td class="cx-text-center">
									<!-- Serialized item toggle -->
									<div v-if="item.serial_no" class="cx-serial-toggle">
										<button
											class="cx-btn cx-btn-sm"
											:class="item.returned_qty > 0 ? 'cx-btn-success' : 'cx-btn-secondary'"
											@click="markSerialReturned(item)"
										>
											{{ item.returned_qty > 0 ? "Scanné (1/1)" : "Non scanné (0/1)" }}
										</button>
									</div>

									<!-- Bulk item stepper -->
									<div v-else class="cx-stepper-control">
										<button class="cx-btn-stepper" @click="incrementBulkReturned(item, -1)">−</button>
										<span class="cx-stepper-value cx-tabular-nums">{{ item.returned_qty }} / {{ item.expected_qty }}</span>
										<button class="cx-btn-stepper" @click="incrementBulkReturned(item, 1)">+</button>
										<button class="cx-btn-stepper-all" title="Tout cocher" @click="returnAllBulk(item)">Max</button>
									</div>
								</td>

								<!-- Condition & Notes -->
								<td>
									<div class="cx-flex cx-items-center cx-gap-2">
										<span
											class="cx-condition-badge"
											:class="{
												'cx-cond-good': item.condition === 'Good',
												'cx-cond-damaged': item.condition === 'Damaged',
												'cx-cond-missing': item.condition === 'Missing',
											}"
										>
											{{ item.condition === 'Good' ? 'Bon état' : item.condition === 'Damaged' ? 'Endommagé' : 'Manquant' }}
										</span>
										<span v-if="item.damage_severity !== 'None'" class="cx-text-xs cx-text-muted">
											({{ item.damage_severity }})
										</span>
									</div>
								</td>

								<!-- Quick Actions -->
								<td class="cx-text-right">
									<div class="cx-flex cx-justify-end cx-gap-1">
										<button
											v-if="item.condition !== 'Damaged'"
											class="cx-btn cx-btn-sm cx-btn-ghost"
											title="Signaler un dommage / panne"
											@click="flagItemForDamage(item)"
										>
											⚠️ Signaler bris
										</button>
										<button
											v-if="item.condition !== 'Missing'"
											class="cx-btn cx-btn-sm cx-btn-ghost cx-text-danger"
											title="Signaler comme manquant"
											@click="flagItemForMissing(item)"
										>
											❌ Manquant
										</button>
										<button
											v-if="item.condition !== 'Good'"
											class="cx-btn cx-btn-sm cx-btn-ghost"
											title="Rétablir en bon état"
											@click="item.condition = 'Good'; item.disposition = 'Return to Stock'; item.damage_severity = 'None';"
										>
											↺ Rétablir
										</button>
									</div>
								</td>
							</tr>
						</tbody>
					</table>
				</div>

				<!-- Step 1 Footer Navigation -->
				<div class="cx-step-footer">
					<div class="cx-text-muted">
						{{ totalReturnedQty }} / {{ totalExpectedQty }} articles scannés.
					</div>
					<div class="cx-flex cx-gap-2">
						<button class="cx-btn cx-btn-primary" @click="currentStep = abnormalItems.length > 0 ? 2 : 3">
							{{ abnormalItems.length > 0 ? "Revue des anomalies (" + abnormalItems.length + ") →" : "Passer au bilan & clôture →" }}
						</button>
					</div>
				</div>
			</section>

			<!-- ------------------------------------------------------------- -->
			<!-- STEP 2 : DIAGNOSTICS & REVUE DES ÉCARTS (BRIS / MANQUANTS)    -->
			<!-- ------------------------------------------------------------- -->
			<section v-if="currentStep === 2" class="cx-step-section">
				<div class="cx-section-header">
					<div>
						<h2 class="cx-title-section">Diagnostic technique et gestion des écarts</h2>
						<p class="cx-text-muted">
							Inspectez les équipements signalés endommagés ou manquants. Définissez leur destination d'atelier et estimez les coûts de remise en état.
						</p>
					</div>
				</div>

				<CortexEmptyState
					v-if="abnormalItems.length === 0"
					title="Aucun bris ou manquant signalé"
					description="Tous les articles sont signalés en bon état pour remise en stock immédiate."
				/>

				<div v-else class="cx-diagnostics-grid">
					<div v-for="item in abnormalItems" :key="item.transaction_item" class="cx-card cx-diagnostic-card">
						<div class="cx-card-header">
							<div>
								<h3 class="cx-title-card">{{ item.item_name }}</h3>
								<div class="cx-flex cx-gap-2 cx-items-center">
									<span class="cx-item-code">{{ item.item_code }}</span>
									<span v-if="item.serial_no" class="cx-serial-tag">🏷️ {{ item.serial_no }}</span>
								</div>
							</div>
							<span
								class="cx-condition-badge"
								:class="item.condition === 'Damaged' ? 'cx-cond-damaged' : 'cx-cond-missing'"
							>
								{{ item.condition === 'Damaged' ? 'Endommagé' : 'Manquant' }}
							</span>
						</div>

						<div class="cx-diagnostic-form">
							<!-- Row 1: Condition & Disposition -->
							<div class="cx-form-grid">
								<div class="cx-form-field">
									<label class="cx-label">Condition constatée</label>
									<select v-model="item.condition" class="cx-select">
										<option value="Good">Bon état (Return to Stock)</option>
										<option value="Damaged">Endommagé / En panne</option>
										<option value="Missing">Manquant / Non restitué</option>
									</select>
								</div>

								<div class="cx-form-field">
									<label class="cx-label">Destination / Disposition stock</label>
									<select v-model="item.disposition" class="cx-select">
										<option value="Return to Stock">Remise en stock direct (Active)</option>
										<option value="Quarantine">Mise en quarantaine (Quarantine)</option>
										<option value="Repair">Envoi en réparation atelier (Under Repair)</option>
										<option value="Missing">Déclaré manquant (Missing)</option>
										<option value="Write-off">Rebut / Perte totale (Decommissioned)</option>
									</select>
								</div>
							</div>

							<!-- Row 2: Severity & Damage Type -->
							<div v-if="item.condition === 'Damaged'" class="cx-form-grid">
								<div class="cx-form-field">
									<label class="cx-label">Sévérité du dommage</label>
									<select v-model="item.damage_severity" class="cx-select">
										<option value="Cosmetic">Cosmétique (rayures légères, traces)</option>
										<option value="Functional">Fonctionnel (panne partielle, connecteur)</option>
										<option value="Blocking">Bloquant (inutilisable / casse majeure)</option>
									</select>
								</div>

								<div class="cx-form-field">
									<label class="cx-label">Type d'avarie constatée</label>
									<select v-model="item.damage_type" class="cx-select">
										<option value="Physical / Impact">Choc physique / Chute</option>
										<option value="Optical Scratch">Rayure optique / Lentille</option>
										<option value="Electronic Failure">Panne électronique / Capteur</option>
										<option value="Liquid / Moisture">Infiltration liquide / Poussière</option>
										<option value="Cable / Connector">Connectique / Câble arraché</option>
										<option value="Missing Parts">Sous-élément / Visserie manquante</option>
										<option value="Other">Autre</option>
									</select>
								</div>
							</div>

							<!-- Row 3: Repair Cost & Detailed Notes -->
							<div class="cx-form-grid">
								<div class="cx-form-field">
									<label class="cx-label">Frais de remise en état estimés ({{ selectedTransaction.currency || 'USD' }})</label>
									<input
										v-model.number="item.estimated_repair_cost"
										type="number"
										min="0"
										step="0.01"
										class="cx-input"
										placeholder="0.00"
									/>
								</div>

								<div class="cx-form-field">
									<label class="cx-label">Rapport d'inspection & Circonstances</label>
									<textarea
										v-model="item.notes"
										rows="2"
										class="cx-textarea"
										placeholder="Détaillez les constatations visuelles ou techniques..."
									/>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Step 2 Footer Navigation -->
				<div class="cx-step-footer">
					<button class="cx-btn cx-btn-secondary" @click="currentStep = 1">
						← Retour au Live Scan
					</button>
					<button class="cx-btn cx-btn-primary" @click="currentStep = 3">
						Passer au Bilan & Clôture →
					</button>
				</div>
			</section>

			<!-- ------------------------------------------------------------- -->
			<!-- STEP 3 : BILAN, RELEVÉ DE RESTITUTION & CLÔTURE              -->
			<!-- ------------------------------------------------------------- -->
			<section v-if="currentStep === 3" class="cx-step-section">
				<div class="cx-section-header">
					<div>
						<h2 class="cx-title-section">Bilan de restitution et finalisation du dossier</h2>
						<p class="cx-text-muted">Vérifiez les totaux, sélectionnez l'option de clôture et validez le retour.</p>
					</div>
				</div>

				<!-- KPI Summary Cards -->
				<div class="cx-kpi-grid">
					<div class="cx-kpi-card">
						<div class="cx-kpi-label">Restitués en bon état</div>
						<div class="cx-kpi-value cx-text-success cx-tabular-nums">{{ totalGoodQty }}</div>
						<div class="cx-kpi-meta">Remis en stock disponible</div>
					</div>

					<div class="cx-kpi-card">
						<div class="cx-kpi-label">Atelier / Quarantaine</div>
						<div class="cx-kpi-value cx-text-warning cx-tabular-nums">{{ totalDamagedQty }}</div>
						<div class="cx-kpi-meta">Indisponibles pour maintenance</div>
					</div>

					<div class="cx-kpi-card">
						<div class="cx-kpi-label">Manquants déclarés</div>
						<div class="cx-kpi-value cx-text-danger cx-tabular-nums">{{ totalMissingQty }}</div>
						<div class="cx-kpi-meta">À facturer ou rechercher</div>
					</div>

					<div class="cx-kpi-card">
						<div class="cx-kpi-label">Estimation frais de remise en état</div>
						<div class="cx-kpi-value cx-tabular-nums">
							{{ formatCurrency(totalEstimatedRepairCost, selectedTransaction.currency || 'USD') }}
						</div>
						<div class="cx-kpi-meta">Retenue de caution / Débit client</div>
					</div>
				</div>

				<!-- Clôture Mode Selector -->
				<div class="cx-panel cx-finalize-mode-panel">
					<h3 class="cx-title-card" style="margin-bottom: var(--space-3)">Option de finalisation du contrat</h3>
					<div class="cx-finalize-options">
						<label class="cx-radio-card" :class="{ 'cx-radio-selected': finalizeMode === 'auto' }">
							<input v-model="finalizeMode" type="radio" value="auto" />
							<div>
								<strong>Automatique (Recommandé)</strong>
								<p class="cx-text-muted">
									{{ isFullyRestituted ? "Tous les articles sont restitués : clôture la transaction vers 'Returned'." : "Retour partiel : enregistre la réception et maintient le contrat en 'Checked Out'." }}
								</p>
							</div>
						</label>

						<label class="cx-radio-card" :class="{ 'cx-radio-selected': finalizeMode === 'settle_with_loss' }">
							<input v-model="finalizeMode" type="radio" value="settle_with_loss" />
							<div>
								<strong>Solder le dossier avec constat de perte</strong>
								<p class="cx-text-muted">
									Clôture définitivement la transaction vers 'Returned' pour lancer la facturation des pertes/frais de réparation.
								</p>
							</div>
						</label>

						<label class="cx-radio-card" :class="{ 'cx-radio-selected': finalizeMode === 'partial' }">
							<input v-model="finalizeMode" type="radio" value="partial" />
							<div>
								<strong>Forcer le maintien en Sortie Active (Checked Out)</strong>
								<p class="cx-text-muted">
									Conserve la transaction ouverte en attente d'un retour ultérieur du reliquat de matériel.
								</p>
							</div>
						</label>
					</div>

					<div class="cx-form-field" style="margin-top: var(--space-4)">
						<label class="cx-label">Notes générales de fin de réception</label>
						<textarea
							v-model="checkinNotes"
							rows="2"
							class="cx-textarea"
							placeholder="Observations générales de l'opérateur de comptoir / entrepôt..."
						/>
					</div>
				</div>

				<CortexErrorState v-if="submitError" :message="submitError" />

				<!-- Step 3 Footer Navigation -->
				<div class="cx-step-footer">
					<button class="cx-btn cx-btn-secondary" @click="currentStep = 2">
						← Modifier les diagnostics
					</button>
					<button
						class="cx-btn cx-btn-primary cx-btn-lg"
						:disabled="submitting"
						@click="submitCheckin"
					>
						{{ submitting ? "Validation en cours..." : "✓ Confirmer et Enregistrer le Check-In" }}
					</button>
				</div>
			</section>
		</div>

		<!-- ============================================================= -->
		<!-- SCREEN C : CONFIRMATION & BON DE RETOUR (PRINT READY)         -->
		<!-- ============================================================= -->
		<div v-else-if="completedReceipt" class="cx-receipt-view">
			<div class="cx-panel cx-receipt-panel">
				<div class="cx-receipt-header">
					<div>
						<h2 class="cx-receipt-title">BON DE RETOUR DE MATÉRIEL</h2>
						<div class="cx-receipt-meta">
							<span>Réf. Check-In : <strong>{{ completedReceipt.id }}</strong></span>
							<span>Contrat de location : <strong>{{ completedReceipt.transaction }}</strong></span>
							<span>Client : <strong>{{ completedReceipt.customer }}</strong></span>
							<span>Date & Heure : <strong>{{ fmtDateTime(completedReceipt.date) }}</strong></span>
							<span>Opérateur : <strong>{{ completedReceipt.operator }}</strong></span>
						</div>
					</div>
					<div class="cx-receipt-status-box">
						<span
							class="cx-badge"
							:class="completedReceipt.fully_returned ? 'cx-cond-good' : 'cx-cond-damaged'"
						>
							{{ completedReceipt.fully_returned ? "RETOUR COMPLET" : "RÉCEPTION PARTIELLE" }}
						</span>
					</div>
				</div>

				<div class="cx-table-container" style="margin-top: var(--space-4)">
					<table class="cx-table">
						<thead>
							<tr>
								<th scope="col">Article</th>
								<th scope="col">Numéro de série</th>
								<th scope="col" class="cx-text-center">Quantité</th>
								<th scope="col">Condition</th>
								<th scope="col">Destination</th>
								<th scope="col" class="cx-text-right">Frais estimés</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="item in completedReceipt.items" :key="item.transaction_item">
								<td>{{ item.item_name }} ({{ item.item_code }})</td>
								<td>{{ item.serial_no || "—" }}</td>
								<td class="cx-text-center">{{ item.returned_qty }} / {{ item.expected_qty }}</td>
								<td>{{ item.condition }}</td>
								<td>{{ item.disposition }}</td>
								<td class="cx-text-right">
									{{ item.estimated_repair_cost > 0 ? formatCurrency(item.estimated_repair_cost) : "0.00" }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>

				<div v-if="completedReceipt.repair_cost > 0" class="cx-receipt-total-bar">
					<span>Total des frais d'avarie / remise en état constatés :</span>
					<strong class="cx-text-danger">{{ formatCurrency(completedReceipt.repair_cost) }}</strong>
				</div>

				<div class="cx-receipt-signatures">
					<div class="cx-sig-box">
						<span>Signature Opérateur Cortex</span>
						<div class="cx-sig-line">{{ completedReceipt.operator }}</div>
					</div>
					<div class="cx-sig-box">
						<span>Visa Renvoyeur / Transporteur</span>
						<div class="cx-sig-line">Bon pour restitution</div>
					</div>
				</div>

				<div class="cx-receipt-actions cx-no-print">
					<button class="cx-btn cx-btn-secondary" @click="navigateToTransaction(completedReceipt.transaction)">
						Consulter la transaction dans le Desk
					</button>
					<button class="cx-btn cx-btn-secondary" @click="printReceipt">
						🖨️ Imprimer le bon de retour
					</button>
					<button class="cx-btn cx-btn-primary" @click="resetSelection">
						+ Démarrer une nouvelle réception
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.cx-checkin-app {
	padding: var(--space-6);
	background: var(--cortex-surface-muted, #f8f9fa);
	min-height: calc(100vh - 60px);
	font-family: var(--font-family-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
	color: var(--cortex-text-primary, #1e293b);
}

.cx-panel {
	background: var(--cortex-surface-card, #ffffff);
	border: 1px solid var(--cortex-border-subtle, #e2e8f0);
	border-radius: var(--radius-lg, 12px);
	padding: var(--space-6);
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

/* Fast Scan Input Bar */
.cx-fast-scan-bar {
	display: flex;
	align-items: center;
	gap: var(--space-3);
	background: #ffffff;
	border: 2px solid var(--cortex-primary-500, #1683dc);
	border-radius: var(--radius-md, 8px);
	padding: var(--space-2) var(--space-4);
	margin-bottom: var(--space-4);
	box-shadow: 0 0 0 4px rgba(22, 131, 220, 0.1);
	transition: all 0.2s ease;
}

.cx-scan-flash-success {
	border-color: #22c55e !important;
	box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.25) !important;
	background: #f0fdf4 !important;
}

.cx-scan-flash-error {
	border-color: #ef4444 !important;
	box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.25) !important;
	background: #fef2f2 !important;
}

.cx-scan-icon {
	font-size: 20px;
	color: var(--cortex-primary-600, #0d72c7);
}

.cx-scan-input {
	flex: 1;
	border: none;
	outline: none;
	font-size: 16px;
	font-weight: 500;
	color: var(--cortex-text-primary, #1e293b);
	background: transparent;
}

.cx-scan-feedback {
	padding: var(--space-2) var(--space-4);
	border-radius: var(--radius-sm, 6px);
	font-size: 13px;
	font-weight: 500;
	margin-bottom: var(--space-4);
}

.cx-feedback-success {
	background: #dcfce7;
	color: #15803d;
}

.cx-feedback-error {
	background: #fee2e2;
	color: #b91c1c;
}

/* Stepper */
.cx-stepper {
	display: flex;
	align-items: center;
	background: #ffffff;
	border: 1px solid var(--cortex-border-subtle, #e2e8f0);
	border-radius: var(--radius-md, 8px);
	padding: var(--space-2) var(--space-4);
	margin-bottom: var(--space-4);
}

.cx-step-tab {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	background: transparent;
	border: none;
	padding: var(--space-2) var(--space-3);
	cursor: pointer;
	color: var(--cortex-text-muted, #64748b);
	font-weight: 500;
	border-radius: var(--radius-sm, 6px);
}

.cx-step-number {
	display: inline-grid;
	place-items: center;
	width: 24px;
	height: 24px;
	border-radius: 50%;
	background: #f1f5f9;
	color: #475569;
	font-size: 12px;
	font-weight: 700;
}

.cx-step-active {
	color: var(--cortex-primary-600, #0d72c7);
	font-weight: 600;
}

.cx-step-active .cx-step-number {
	background: var(--cortex-primary-500, #1683dc);
	color: #ffffff;
}

.cx-step-done .cx-step-number {
	background: #22c55e;
	color: #ffffff;
}

.cx-step-alert {
	color: #b45309;
}

.cx-step-divider {
	flex: 1;
	height: 1px;
	background: var(--cortex-border-subtle, #e2e8f0);
	margin: 0 var(--space-2);
}

.cx-badge-count {
	background: #f59e0b;
	color: #ffffff;
	font-size: 11px;
	padding: 1px 6px;
	border-radius: 999px;
	margin-left: 4px;
}

/* Summary Banner */
.cx-txn-summary-banner {
	display: flex;
	align-items: center;
	justify-content: space-between;
	background: #ffffff;
	border: 1px solid var(--cortex-border-subtle, #e2e8f0);
	border-radius: var(--radius-md, 8px);
	padding: var(--space-3) var(--space-4);
	margin-bottom: var(--space-4);
	flex-wrap: wrap;
	gap: var(--space-3);
}

.cx-summary-meta {
	display: flex;
	align-items: center;
	gap: var(--space-4);
	flex-wrap: wrap;
}

.cx-summary-id {
	font-weight: 700;
	color: var(--cortex-primary-700, #095da8);
}

.cx-summary-stats {
	display: flex;
	gap: var(--space-2);
}

.cx-stat-pill {
	font-size: 13px;
	background: #f8fafc;
	border: 1px solid #e2e8f0;
	padding: 4px 10px;
	border-radius: 999px;
}

.cx-pill-warning {
	background: #fffbeb;
	border-color: #fde68a;
	color: #b45309;
}

.cx-pill-danger {
	background: #fef2f2;
	border-color: #fecaca;
	color: #b91c1c;
}

/* Tables */
.cx-table-container {
	background: #ffffff;
	border: 1px solid var(--cortex-border-subtle, #e2e8f0);
	border-radius: var(--radius-md, 8px);
	overflow-x: auto;
}

.cx-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 13px;
}

.cx-table th {
	background: #f8fafc;
	padding: 10px 14px;
	text-align: left;
	font-weight: 600;
	color: #475569;
	border-bottom: 1px solid #e2e8f0;
}

.cx-table td {
	padding: 12px 14px;
	border-bottom: 1px solid #f1f5f9;
	vertical-align: middle;
}

.cx-row-interactive {
	cursor: pointer;
	transition: background 0.15s ease;
}

.cx-row-interactive:hover {
	background: #f8fafc;
}

.cx-row-scanned {
	background: #f0fdf4;
}

.cx-row-damaged {
	background: #fffbeb;
}

.cx-row-missing {
	background: #fef2f2;
}

/* Stepper control */
.cx-stepper-control {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	border: 1px solid #cbd5e1;
	border-radius: 6px;
	padding: 2px 4px;
	background: #ffffff;
}

.cx-btn-stepper {
	background: #f1f5f9;
	border: 1px solid #e2e8f0;
	border-radius: 4px;
	width: 24px;
	height: 24px;
	font-weight: 700;
	cursor: pointer;
}

.cx-btn-stepper-all {
	background: #e0f2fe;
	color: #0284c7;
	border: none;
	border-radius: 4px;
	padding: 2px 6px;
	font-size: 11px;
	font-weight: 600;
	cursor: pointer;
}

.cx-stepper-value {
	font-weight: 600;
	font-size: 12px;
	padding: 0 4px;
}

.cx-serial-tag {
	display: inline-block;
	background: #eff6ff;
	color: #1d4ed8;
	border: 1px solid #bfdbfe;
	padding: 2px 8px;
	border-radius: 4px;
	font-size: 12px;
	font-weight: 500;
}

.cx-condition-badge {
	display: inline-block;
	padding: 2px 8px;
	border-radius: 999px;
	font-size: 12px;
	font-weight: 600;
}

.cx-cond-good {
	background: #dcfce7;
	color: #15803d;
}

.cx-cond-damaged {
	background: #fef3c7;
	color: #b45309;
}

.cx-cond-missing {
	background: #fee2e2;
	color: #b91c1c;
}

.cx-badge-icon {
	display: inline-grid;
	place-items: center;
	width: 24px;
	height: 24px;
	border-radius: 50%;
	font-size: 12px;
	font-weight: 700;
}

.cx-icon-success {
	background: #dcfce7;
	color: #16a34a;
}

.cx-icon-warning {
	background: #fef3c7;
	color: #d97706;
}

.cx-icon-danger {
	background: #fee2e2;
	color: #dc2626;
}

.cx-icon-pending {
	background: #f1f5f9;
	color: #94a3b8;
}

/* Diagnostics Step */
.cx-diagnostics-grid {
	display: grid;
	grid-template-columns: 1fr;
	gap: var(--space-4);
}

.cx-diagnostic-card {
	background: #ffffff;
	border: 1px solid #e2e8f0;
	border-radius: var(--radius-lg, 12px);
	padding: var(--space-4);
}

.cx-card-header {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	border-bottom: 1px solid #f1f5f9;
	padding-bottom: var(--space-3);
	margin-bottom: var(--space-3);
}

.cx-title-card {
	font-size: 16px;
	font-weight: 700;
	margin: 0 0 4px;
}

.cx-form-grid {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: var(--space-4);
	margin-bottom: var(--space-3);
}

@media (max-width: 768px) {
	.cx-form-grid {
		grid-template-columns: 1fr;
	}
}

.cx-form-field {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.cx-label {
	font-size: 12px;
	font-weight: 600;
	color: #475569;
}

.cx-select,
.cx-input,
.cx-textarea {
	border: 1px solid #cbd5e1;
	border-radius: 6px;
	padding: 8px 10px;
	font-size: 13px;
	color: #1e293b;
	background: #ffffff;
}

.cx-select:focus,
.cx-input:focus,
.cx-textarea:focus {
	outline: none;
	border-color: var(--cortex-primary-500, #1683dc);
	box-shadow: 0 0 0 3px rgba(22, 131, 220, 0.15);
}

/* KPI Grid */
.cx-kpi-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
	gap: var(--space-4);
	margin-bottom: var(--space-6);
}

.cx-kpi-card {
	background: #ffffff;
	border: 1px solid #e2e8f0;
	border-radius: var(--radius-md, 8px);
	padding: var(--space-4);
	text-align: center;
}

.cx-kpi-label {
	font-size: 13px;
	color: #64748b;
	margin-bottom: 4px;
}

.cx-kpi-value {
	font-size: 24px;
	font-weight: 700;
	color: #1e293b;
}

.cx-kpi-meta {
	font-size: 11px;
	color: #94a3b8;
	margin-top: 4px;
}

/* Finalize Options */
.cx-finalize-options {
	display: grid;
	grid-template-columns: 1fr;
	gap: var(--space-3);
}

.cx-radio-card {
	display: flex;
	align-items: flex-start;
	gap: var(--space-3);
	padding: var(--space-3) var(--space-4);
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	cursor: pointer;
	transition: all 0.15s ease;
}

.cx-radio-selected {
	border-color: var(--cortex-primary-500, #1683dc);
	background: #eff6ff;
}

/* Step Footers & Toolbars */
.cx-step-footer {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-top: var(--space-6);
	padding-top: var(--space-4);
	border-top: 1px solid #e2e8f0;
}

.cx-scan-toolbar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: var(--space-3);
}

/* Buttons */
.cx-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
	padding: 8px 16px;
	border-radius: 6px;
	font-size: 13px;
	font-weight: 600;
	cursor: pointer;
	border: 1px solid transparent;
	transition: all 0.15s ease;
}

.cx-btn-sm {
	padding: 4px 10px;
	font-size: 12px;
}

.cx-btn-lg {
	padding: 12px 24px;
	font-size: 15px;
}

.cx-btn-primary {
	background: var(--cortex-primary-500, #1683dc);
	color: #ffffff;
}

.cx-btn-primary:hover {
	background: var(--cortex-primary-600, #0d72c7);
}

.cx-btn-secondary {
	background: #ffffff;
	border-color: #cbd5e1;
	color: #334155;
}

.cx-btn-secondary:hover {
	background: #f8fafc;
}

.cx-btn-ghost {
	background: transparent;
	color: #64748b;
}

.cx-btn-ghost:hover {
	background: #f1f5f9;
	color: #0f172a;
}

.cx-btn-success {
	background: #dcfce7;
	border-color: #86efac;
	color: #15803d;
}

/* Receipt Print Styling */
.cx-receipt-panel {
	max-width: 800px;
	margin: 0 auto;
}

.cx-receipt-header {
	display: flex;
	justify-content: space-between;
	border-bottom: 2px solid #0f172a;
	padding-bottom: var(--space-4);
}

.cx-receipt-title {
	font-size: 20px;
	font-weight: 800;
	letter-spacing: 0.5px;
	margin: 0 0 var(--space-2);
}

.cx-receipt-meta {
	display: flex;
	flex-direction: column;
	gap: 2px;
	font-size: 13px;
	color: #334155;
}

.cx-receipt-total-bar {
	display: flex;
	justify-content: space-between;
	font-size: 16px;
	padding: var(--space-3) 0;
	border-top: 1px dashed #cbd5e1;
	border-bottom: 1px dashed #cbd5e1;
	margin-top: var(--space-4);
}

.cx-receipt-signatures {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: var(--space-8);
	margin-top: var(--space-8);
	padding-top: var(--space-4);
}

.cx-sig-box {
	display: flex;
	flex-direction: column;
	font-size: 12px;
	color: #64748b;
}

.cx-sig-line {
	margin-top: 40px;
	border-top: 1px solid #94a3b8;
	padding-top: 4px;
	font-weight: 600;
	color: #1e293b;
}

.cx-receipt-actions {
	display: flex;
	justify-content: flex-end;
	gap: var(--space-3);
	margin-top: var(--space-6);
	padding-top: var(--space-4);
	border-top: 1px solid #e2e8f0;
}

@media print {
	.cx-no-print,
	.cx-page-header,
	.cx-stepper {
		display: none !important;
	}
	.cx-checkin-app {
		background: #ffffff;
		padding: 0;
	}
	.cx-panel {
		border: none;
		box-shadow: none;
		padding: 0;
	}
}
</style>
