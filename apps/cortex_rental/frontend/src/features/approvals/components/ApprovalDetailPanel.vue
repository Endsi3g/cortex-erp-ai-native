<template>
  <div class="bg-cortex-surface border border-cortex-border rounded-2xl p-5 sm:p-6 space-y-6 shadow-sm">
    <!-- Header -->
    <div class="flex flex-wrap items-start justify-between gap-4 border-b border-cortex-border pb-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-cortex-surface-muted border border-cortex-border text-cortex-text-muted">
            {{ approval.id }}
          </span>
          <span
            class="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5"
            :class="getStatusBadgeClass(approval.status)"
          >
            <component :is="getStatusIcon(approval.status)" class="w-3.5 h-3.5" />
            <span>{{ getStatusLabel(approval.status) }}</span>
          </span>
        </div>
        <h2 class="text-lg font-bold text-cortex-text-primary mt-2">
          {{ approval.title }}
        </h2>
        <div class="text-xs text-cortex-text-muted mt-0.5">
          Type : <strong>{{ approval.approval_type }}</strong> • Créé le {{ formatDate(approval.created_at) }}
        </div>
      </div>

      <button
        v-if="showClose"
        type="button"
        class="p-2 text-cortex-text-muted hover:text-cortex-text-primary rounded-lg hover:bg-cortex-surface-muted transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center lg:hidden"
        aria-label="Fermer"
        @click="$emit('close')"
      >
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Requester & Target Entity Card -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="p-3.5 rounded-xl border border-cortex-border bg-cortex-surface-muted/50 space-y-1">
        <div class="text-[11px] font-bold uppercase tracking-wider text-cortex-text-muted">
          Demandeur de l'action
        </div>
        <div class="flex items-center gap-2">
          <span
            class="p-1 rounded-md text-xs font-bold flex items-center gap-1"
            :class="approval.requested_by_type === 'Agent' ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-800'"
          >
            <Sparkles v-if="approval.requested_by_type === 'Agent'" class="w-3.5 h-3.5 text-purple-600" />
            <User v-else class="w-3.5 h-3.5 text-slate-600" />
            <span>{{ approval.requested_by_type === 'Agent' ? 'Agent IA Onyx' : 'Opérateur Humain' }}</span>
          </span>
          <span class="text-xs font-medium text-cortex-text-primary">{{ approval.requested_by }}</span>
        </div>
      </div>

      <div class="p-3.5 rounded-xl border border-cortex-border bg-cortex-surface-muted/50 space-y-1">
        <div class="text-[11px] font-bold uppercase tracking-wider text-cortex-text-muted">
          Entité référencée
        </div>
        <div class="flex items-center gap-2 text-xs">
          <FileText class="w-4 h-4 text-cortex-primary" />
          <router-link
            v-if="approval.reference_doctype === 'Cortex Rental Transaction'"
            :to="`/rentals/${approval.reference_name}`"
            class="font-mono font-bold text-cortex-primary hover:underline"
          >
            {{ approval.reference_name }}
          </router-link>
          <span v-else class="font-mono font-bold text-cortex-text-primary">
            {{ approval.reference_name }}
          </span>
          <span class="text-[10px] text-cortex-text-muted">({{ approval.reference_doctype }})</span>
        </div>
      </div>
    </div>

    <!-- Threshold Alert -->
    <div
      v-if="approval.threshold_exceeded_details"
      class="p-3.5 rounded-xl border border-amber-300 bg-amber-50 text-xs text-amber-950 flex items-start gap-2.5"
    >
      <AlertTriangle class="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
      <div>
        <div class="font-bold uppercase tracking-wider text-[11px] text-amber-900">Seuil de politique dépassé</div>
        <p class="mt-0.5">{{ approval.threshold_exceeded_details }}</p>
      </div>
    </div>

    <!-- Description -->
    <div class="space-y-1.5">
      <div class="text-xs font-bold uppercase tracking-wider text-cortex-text-muted">
        Description de la demande
      </div>
      <p class="text-sm text-cortex-text-primary leading-relaxed bg-cortex-surface-muted/30 p-3.5 rounded-xl border border-cortex-border">
        {{ approval.description }}
      </p>
    </div>

    <!-- Comparative Diff Card -->
    <ApprovalDiffCard
      :before-state="approval.before_state"
      :after-state="approval.after_state"
    />

    <!-- Evidence IDs / Justificatifs -->
    <div v-if="approval.evidence_ids && approval.evidence_ids.length > 0" class="space-y-2">
      <div class="text-xs font-bold uppercase tracking-wider text-cortex-text-muted flex items-center gap-1.5">
        <Paperclip class="w-3.5 h-3.5" />
        <span>Pièces justificatives & Preuves ({{ approval.evidence_ids.length }})</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="evId in approval.evidence_ids"
          :key="evId"
          type="button"
          class="px-3 py-1.5 rounded-lg border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-xs font-mono text-cortex-text-primary flex items-center gap-1.5 transition-colors min-h-[36px]"
          @click="inspectEvidence(evId)"
        >
          <FileCheck class="w-3.5 h-3.5 text-emerald-600" />
          <span>{{ evId }}</span>
          <ExternalLink class="w-3 h-3 text-cortex-text-muted ml-0.5" />
        </button>
      </div>
    </div>

    <!-- Anti-Self-Approval & Security Protocol Banner -->
    <div class="p-3.5 bg-cortex-primary/5 border border-cortex-primary/20 rounded-xl text-xs text-cortex-text-secondary flex items-start gap-2.5">
      <ShieldCheck class="w-4 h-4 shrink-0 text-cortex-primary mt-0.5" />
      <div>
        <div class="font-bold text-cortex-text-primary">Règle de Supervision R5 — SAS d'Approbation Humaine</div>
        <p class="text-cortex-text-muted mt-0.5">
          Les agents IA ne peuvent en aucun cas auto-valider une demande. Cette validation exécutera les mutations en base, déclenchera les écritures ERPNext et générera un événement d'audit immuable.
        </p>
      </div>
    </div>

    <!-- Resolved State Info (if already approved/rejected) -->
    <div
      v-if="approval.status === 'approved'"
      class="p-4 rounded-xl border border-emerald-300 bg-emerald-50 text-xs text-emerald-950 flex items-center gap-3"
    >
      <CheckCircle2 class="w-5 h-5 text-emerald-600 shrink-0" />
      <div>
        <div class="font-bold">Demande approuvée et exécutée</div>
        <div class="text-emerald-800 text-[11px] mt-0.5">
          Par {{ approval.resolved_by || 'Superviseur' }} le {{ formatDate(approval.resolved_at || approval.created_at) }}
        </div>
      </div>
    </div>

    <div
      v-else-if="approval.status === 'rejected'"
      class="p-4 rounded-xl border border-red-300 bg-red-50 text-xs text-red-950 flex items-start gap-3"
    >
      <XCircle class="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
      <div>
        <div class="font-bold">Demande rejetée</div>
        <div class="text-red-800 text-[11px] mt-0.5">
          Par {{ approval.resolved_by || 'Superviseur' }} le {{ formatDate(approval.resolved_at || approval.created_at) }}
        </div>
        <div v-if="approval.rejection_reason" class="mt-1 font-semibold text-red-900 bg-red-100/60 p-2 rounded">
          Motif : {{ approval.rejection_reason }}
        </div>
      </div>
    </div>

    <!-- Action Buttons (Only if pending) -->
    <div
      v-if="approval.status === 'pending'"
      class="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-cortex-border"
    >
      <button
        type="button"
        class="px-4 py-2.5 rounded-xl border border-red-300 bg-red-50 hover:bg-red-100 text-red-800 text-xs font-bold transition-colors min-h-[44px] flex items-center gap-1.5"
        :disabled="isSubmittingApproval"
        @click="showRejectModal = true"
      >
        <XCircle class="w-4 h-4 text-red-600" />
        <span>{{ $t('approvals.reject_action', 'Rejeter avec motif...') }}</span>
      </button>

      <button
        type="button"
        class="px-6 py-2.5 rounded-xl bg-cortex-primary hover:bg-cortex-primary-hover text-white text-xs font-bold shadow-sm transition-colors min-h-[44px] flex items-center gap-2 disabled:opacity-50"
        :disabled="isSubmittingApproval"
        @click="handleApprove"
      >
        <Loader2 v-if="isSubmittingApproval" class="w-4 h-4 animate-spin" />
        <ShieldCheck v-else class="w-4 h-4" />
        <span>{{ $t('approvals.approve_action', 'Approuver et Exécuter') }}</span>
      </button>
    </div>

    <!-- Modals -->
    <ApprovalRejectModal
      :is-open="showRejectModal"
      :request-id="approval.id"
      :title="approval.title"
      @close="showRejectModal = false"
      @rejected="handleRejected"
    />

    <!-- Evidence Preview Modal -->
    <div
      v-if="inspectedEvidenceId"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
    >
      <div class="bg-cortex-surface border border-cortex-border rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4">
        <div class="flex items-center justify-between border-b border-cortex-border pb-3">
          <div class="flex items-center gap-2">
            <FileText class="w-5 h-5 text-cortex-primary" />
            <h4 class="text-sm font-bold text-cortex-text-primary">Preuve / Justificatif</h4>
          </div>
          <button
            class="p-1 rounded-lg text-cortex-text-muted hover:text-cortex-text-primary"
            @click="inspectedEvidenceId = null"
          >
            <X class="w-5 h-5" />
          </button>
        </div>
        <div class="p-4 bg-cortex-surface-muted rounded-xl space-y-2 text-xs font-mono">
          <div><span class="text-cortex-text-muted">Evidence ID:</span> {{ inspectedEvidenceId }}</div>
          <div><span class="text-cortex-text-muted">Type:</span> Certificat / Document PDF</div>
          <div><span class="text-cortex-text-muted">Horodatage:</span> {{ approval.created_at }}</div>
          <div><span class="text-cortex-text-muted">Hash SHA-256:</span> e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</div>
        </div>
        <div class="flex justify-end pt-2">
          <button
            type="button"
            class="px-4 py-2 bg-cortex-surface border border-cortex-border text-xs font-semibold rounded-xl"
            @click="inspectedEvidenceId = null"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileCheck,
  FileText,
  Loader2,
  Lock,
  Paperclip,
  ShieldCheck,
  Sparkles,
  User,
  X,
  XCircle
} from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { ApprovalRequestItem } from '@/api/contracts'
import ApprovalDiffCard from './ApprovalDiffCard.vue'
import ApprovalRejectModal from './ApprovalRejectModal.vue'

const props = withDefaults(
  defineProps<{
    approval: ApprovalRequestItem
    showClose?: boolean
  }>(),
  {
    showClose: false
  }
)

const emit = defineEmits<{
  (e: 'approved', id: string): void
  (e: 'rejected', id: string, reason: string): void
  (e: 'close'): void
}>()

const showRejectModal = ref(false)
const isSubmittingApproval = ref(false)
const inspectedEvidenceId = ref<string | null>(null)

function inspectEvidence(evId: string) {
  inspectedEvidenceId.value = evId
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('fr-CA', {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'pending': return 'Supervision Requise'
    case 'approved': return 'Approuvé'
    case 'rejected': return 'Rejeté'
    case 'expired': return 'Expiré'
    default: return status
  }
}

function getStatusBadgeClass(status: string): string {
  switch (status) {
    case 'pending': return 'bg-amber-100 text-amber-900 border border-amber-300'
    case 'approved': return 'bg-emerald-100 text-emerald-900 border border-emerald-300'
    case 'rejected': return 'bg-red-100 text-red-900 border border-red-300'
    default: return 'bg-slate-100 text-slate-800 border border-slate-300'
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'pending': return Lock
    case 'approved': return ShieldCheck
    case 'rejected': return XCircle
    default: return AlertTriangle
  }
}

async function handleApprove() {
  isSubmittingApproval.value = true
  try {
    const client = getCortexApiClient()
    const res = await client.approveApprovalRequest({
      id: props.approval.id,
      notes: 'Approbation managériale validée depuis le SAS Cortex.'
    })

    if (res.status === 'completed') {
      emit('approved', props.approval.id)
    }
  } catch (err) {
    console.error('Approve failed', err)
  } finally {
    isSubmittingApproval.value = false
  }
}

function handleRejected(reason: string) {
  emit('rejected', props.approval.id, reason)
}
</script>
