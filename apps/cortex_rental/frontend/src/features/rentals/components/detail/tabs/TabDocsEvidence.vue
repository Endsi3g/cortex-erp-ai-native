<template>
  <div class="space-y-5 text-xs" data-test="tab-docs-evidence">
    <!-- Existing Documents Card -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3">
      <h3 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px]">
        Documents Contractuels & Pièces Justificatives
      </h3>

      <div class="divide-y divide-cortex-border">
        <div
          v-for="doc in documents"
          :key="doc.id"
          class="py-2.5 flex items-center justify-between"
        >
          <div class="flex items-center gap-2.5">
            <FileText class="w-4 h-4 text-cortex-primary-600 flex-shrink-0" />
            <div>
              <span class="font-semibold text-cortex-text-primary block">{{ doc.title }}</span>
              <span class="font-mono text-[10px] text-cortex-text-muted">{{ doc.id }} • {{ doc.date }}</span>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-cortex-primary-50 text-cortex-primary-800 border border-cortex-primary-200">
              Vérifié
            </span>
            <button
              type="button"
              class="cx-btn-secondary text-[11px] px-2 py-1 flex items-center gap-1"
              @click="simulatedDownload(doc.title)"
            >
              <Download class="w-3 h-3" />
              <span>Télécharger</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Upload Evidence Intent Flow Simulator (R12) -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3" data-test="upload-evidence-simulator">
      <div class="flex items-center justify-between">
        <h4 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px]">
          Téléversement Sécurisé de Preuve (Flow UploadIntent)
        </h4>
        <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cortex-surface-secondary text-cortex-text-muted border border-cortex-border">
          SHA-256 Verifié Serveur
        </span>
      </div>

      <div class="p-4 rounded-lg border-2 border-dashed border-cortex-border text-center space-y-2 hover:border-cortex-primary-400 transition-colors">
        <UploadCloud class="w-8 h-8 text-cortex-primary-600 mx-auto" />
        <p class="text-cortex-text-secondary font-medium">
          Glisser-déposer une pièce justificative ou un constat d'incident
        </p>
        <p class="text-[10px] text-cortex-text-muted">
          Formats acceptés : PDF, PNG, JPEG (Max 25 Mo). Hachage cryptographique automatique.
        </p>
        <button
          type="button"
          class="cx-btn-secondary text-xs px-3 py-1.5"
          :disabled="isUploading"
          @click="simulateUpload"
        >
          <span v-if="isUploading">Vérification de l'UploadIntent...</span>
          <span v-else>Simuler téléversement de preuve</span>
        </button>
      </div>

      <div
        v-if="uploadFeedback"
        class="p-2.5 rounded-lg border border-cortex-primary-300 bg-cortex-primary-50 text-xs text-cortex-primary-950 flex items-center justify-between"
      >
        <div class="flex items-center gap-2">
          <CheckCircle2 class="w-4 h-4 text-cortex-primary-700" />
          <span>{{ uploadFeedback }}</span>
        </div>
        <span class="font-mono text-[10px] font-bold text-cortex-primary-800">
          DEMO-EVD-NEW
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { FileText, Download, UploadCloud, CheckCircle2 } from 'lucide-vue-next'
import type { RentalTransaction } from '@/types/rental'

const props = defineProps<{
  rental: RentalTransaction
}>()

const isUploading = ref(false)
const uploadFeedback = ref<string | null>(null)

const documents = [
  { id: 'DEMO-DOC-001', title: 'Bon de Soumission Officiel (Quote)', date: props.rental.created_at.slice(0, 10) },
  { id: 'DEMO-DOC-002', title: 'Contrat de Location & Conditions Générales', date: props.rental.starts_at.slice(0, 10) },
  { id: 'DEMO-DOC-003', title: 'Certificat d’Assurance Tournage Responsabilité Civile', date: '2026-08-15' }
]

const simulatedDownload = (title: string) => {
  alert(`Téléchargement de ${title} (${props.rental.name})`)
}

const simulateUpload = () => {
  isUploading.value = true
  uploadFeedback.value = null
  setTimeout(() => {
    isUploading.value = false
    uploadFeedback.value = 'Preuve téléversée, scannée et scellée avec audit event cortex.evidence.uploaded.'
  }, 600)
}
</script>
