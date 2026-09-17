<script setup>
import { ref } from "vue";
import { ICONS } from "./CortexIcons.js";

const props = defineProps({
	mode: { type: String, default: "quote" }, // 'quote' | 'insurance'
	title: { type: String, default: "Ingestion Documentaire IA" },
});

const emit = defineEmits(["extracted"]);

const isDragging = ref(false);
const isProcessing = ref(false);
const progressStep = ref("");
const extractedResult = ref(null);

const DEMO_FILES = {
	quote: {
		fileName: "Devis_Technique_Dune3_Prod_v2.pdf",
		confidence: 98.6,
		items: [
			{ code: "ARRI-ALX35", label: "ARRI Alexa 35 Camera Package", qty: 2, confidence: 99 },
			{ code: "COOKE-S4I-SET", label: "Cooke S4/i Prime Set (6x Lenses)", qty: 1, confidence: 98 },
			{ code: "APUTURE-1200D", label: "Aputure Electro Storm 1200D Daylight", qty: 3, confidence: 97 },
			{ code: "BNC-50FT", label: "12G-SDI BNC Cable 50ft", qty: 8, confidence: 100 },
			{ code: "C-STAND-40", label: "Avenger C-Stand 40 with Grip Arm", qty: 6, confidence: 100 },
		],
		notes: "Tournage prévu du 01/10/2026 au 14/10/2026 (14 jours de location, dégressivité 7j=3j applicable).",
	},
	insurance: {
		fileName: "Attestation_Assurance_Tournage_HBO_2026.pdf",
		confidence: 99.2,
		data: {
			insurer: "Chubb Insurance Company of Canada",
			policyNumber: "CA-ENT-2026-99410",
			validFrom: "2026-06-01",
			validTo: "2027-05-31",
			coverageAmount: "5 000 000 $ CAD",
			deductible: "2 500 $ CAD",
			cortexMentioned: true,
		},
		notes: "Cortex Rentals Inc. est expressément désignée comme bénéficiaire additionnel des indemnités d'assurance.",
	},
};

function handleDrop(e) {
	e.preventDefault();
	isDragging.value = false;
	simulateExtraction();
}

function simulateExtraction(fileKey) {
	isProcessing.value = true;
	extractedResult.value = null;
	progressStep.value = "Analyse OCR et segmentation du document…";

	setTimeout(() => {
		progressStep.value = "Validation sémantique & extraction JSON typé…";
		setTimeout(() => {
			progressStep.value = "Calcul de la politique de sécurité & confiance…";
			setTimeout(() => {
				isProcessing.value = false;
				extractedResult.value = DEMO_FILES[props.mode];
			}, 400);
		}, 400);
	}, 400);
}

function applyExtraction() {
	if (!extractedResult.value) return;
	emit("extracted", extractedResult.value);
	extractedResult.value = null;
}

function cancel() {
	extractedResult.value = null;
	isProcessing.value = false;
}
</script>

<template>
	<div class="cx-ingestor cx-surface">
		<div class="cx-ingestor-header">
			<div class="cx-ingestor-title-wrap">
				<span class="cx-icon-sm cx-emerald" v-html="ICONS.sparkles"></span>
				<h4 class="cx-ingestor-title">{{ title }}</h4>
			</div>
			<span class="cx-badge cx-badge-success">Extraction Structurée</span>
		</div>

		<!-- Drop Zone -->
		<div
			v-if="!extractedResult && !isProcessing"
			class="cx-dropzone"
			:class="{ 'is-dragging': isDragging }"
			@dragover.prevent="isDragging = true"
			@dragleave.prevent="isDragging = false"
			@drop="handleDrop"
			@click="simulateExtraction"
		>
			<div class="cx-dropzone-icon" v-html="ICONS.fileText"></div>
			<p class="cx-dropzone-text">
				Glissez-déposez un document PDF ici, ou <strong>cliquez pour charger un exemple</strong>
			</p>
			<p class="cx-dropzone-hint">
				Formats acceptés : PDF, listes techniques, devis de production, certificats d'assurance.
			</p>
		</div>

		<!-- Processing State -->
		<div v-if="isProcessing" class="cx-ingestor-processing">
			<div class="cx-spinner-wrap">
				<span class="cx-icon-spin cx-emerald" v-html="ICONS.refresh"></span>
			</div>
			<p class="cx-processing-step">{{ progressStep }}</p>
			<span class="cx-text-meta">Pipeline FastMCP &amp; Agent Onyx Cortex</span>
		</div>

		<!-- Extraction Result Preview -->
		<div v-if="extractedResult" class="cx-extraction-preview">
			<div class="cx-preview-header">
				<div class="cx-preview-meta">
					<span class="cx-preview-filename">{{ extractedResult.fileName }}</span>
					<span class="cx-badge cx-badge-success">Confiance IA : {{ extractedResult.confidence }}%</span>
				</div>
				<div class="cx-preview-actions">
					<button type="button" class="cx-btn cx-btn-ghost" @click="cancel">Réinitialiser</button>
					<button type="button" class="cx-btn cx-btn-primary" @click="applyExtraction">
						✓ Injecter dans le système
					</button>
				</div>
			</div>

			<!-- Quote Mode Items -->
			<div v-if="mode === 'quote' && extractedResult.items" class="cx-extracted-table-wrap">
				<table class="cx-table cx-extracted-table">
					<thead>
						<tr>
							<th>Code Profil</th>
							<th>Désignation Équipement</th>
							<th style="text-align: right">Quantité</th>
							<th style="text-align: right">Score</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="item in extractedResult.items" :key="item.code">
							<td><code>{{ item.code }}</code></td>
							<td>{{ item.label }}</td>
							<td style="text-align: right; font-weight: 600">{{ item.qty }}</td>
							<td style="text-align: right">
								<span class="cx-score-pill">{{ item.confidence }}%</span>
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<!-- Insurance Mode Data -->
			<div v-if="mode === 'insurance' && extractedResult.data" class="cx-insurance-grid">
				<div class="cx-data-tile">
					<span class="cx-text-label">Compagnie d'Assurance</span>
					<div class="cx-data-val">{{ extractedResult.data.insurer }}</div>
				</div>
				<div class="cx-data-tile">
					<span class="cx-text-label">Numéro de Police</span>
					<div class="cx-data-val"><code>{{ extractedResult.data.policyNumber }}</code></div>
				</div>
				<div class="cx-data-tile">
					<span class="cx-text-label">Plafond Couvert</span>
					<div class="cx-data-val" style="color: var(--cortex-primary-700)">{{ extractedResult.data.coverageAmount }}</div>
				</div>
				<div class="cx-data-tile">
					<span class="cx-text-label">Validité</span>
					<div class="cx-data-val">{{ extractedResult.data.validFrom }} au {{ extractedResult.data.validTo }}</div>
				</div>
			</div>

			<p class="cx-extracted-notes">{{ extractedResult.notes }}</p>
		</div>
	</div>
</template>

<style scoped>
.cx-ingestor {
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	padding: var(--space-4);
	margin-bottom: var(--space-4);
}

.cx-ingestor-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: var(--space-3);
}

.cx-ingestor-title-wrap {
	display: flex;
	align-items: center;
	gap: var(--space-2);
}

.cx-ingestor-title {
	font-size: 13.5px;
	font-weight: 600;
	margin: 0;
	color: var(--cortex-text-primary);
}

.cx-emerald {
	color: var(--cortex-primary-600);
}

.cx-dropzone {
	border: 1.5px dashed var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-6) var(--space-4);
	text-align: center;
	cursor: pointer;
	background: var(--cortex-surface-muted);
	transition: all 0.15s ease;
}

.cx-dropzone:hover,
.cx-dropzone.is-dragging {
	border-color: var(--cortex-primary-500);
	background: var(--cortex-primary-50);
}

.cx-dropzone-icon {
	color: var(--cortex-primary-600);
	margin-bottom: var(--space-2);
}

.cx-dropzone-text {
	font-size: 13px;
	color: var(--cortex-text-primary);
	margin: 0 0 var(--space-1);
}

.cx-dropzone-hint {
	font-size: 11px;
	color: var(--cortex-text-muted);
	margin: 0;
}

.cx-ingestor-processing {
	padding: var(--space-6);
	text-align: center;
	background: var(--cortex-surface-muted);
	border-radius: var(--radius-md);
}

.cx-spinner-wrap {
	margin-bottom: var(--space-2);
}

.cx-icon-spin {
	display: inline-block;
	animation: spin 1s linear infinite;
}

@keyframes spin {
	from {
		transform: rotate(0deg);
	}
	to {
		transform: rotate(360deg);
	}
}

.cx-processing-step {
	font-size: 13px;
	font-weight: 500;
	color: var(--cortex-text-primary);
	margin: 0 0 var(--space-1);
}

.cx-extraction-preview {
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-primary-200);
	border-radius: var(--radius-md);
	padding: var(--space-3);
}

.cx-preview-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: var(--space-3);
	padding-bottom: var(--space-2);
	border-bottom: 1px solid var(--cortex-border);
}

.cx-preview-meta {
	display: flex;
	align-items: center;
	gap: var(--space-2);
}

.cx-preview-filename {
	font-size: 13px;
	font-weight: 600;
	color: var(--cortex-text-primary);
}

.cx-preview-actions {
	display: flex;
	gap: var(--space-2);
}

.cx-extracted-table {
	font-size: 12px;
	margin-bottom: var(--space-2);
}

.cx-score-pill {
	font-size: 10.5px;
	font-family: var(--font-mono);
	padding: 1px 5px;
	background: var(--cortex-primary-50);
	color: var(--cortex-primary-700);
	border-radius: 3px;
}

.cx-insurance-grid {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: var(--space-3);
	margin-bottom: var(--space-3);
}

.cx-data-tile {
	padding: var(--space-2);
	background: var(--cortex-surface-muted);
	border-radius: var(--radius-sm);
}

.cx-data-val {
	font-size: 13px;
	font-weight: 600;
	color: var(--cortex-text-primary);
	margin-top: 2px;
}

.cx-extracted-notes {
	font-size: 11.5px;
	color: var(--cortex-text-muted);
	margin: var(--space-2) 0 0;
	font-style: italic;
}
</style>
