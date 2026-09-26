<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto"
    role="dialog"
    aria-modal="true"
    aria-labelledby="reject-modal-title"
  >
    <div
      class="bg-cortex-surface border border-cortex-border rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150"
    >
      <!-- Header -->
      <div class="flex items-start justify-between border-b border-cortex-border pb-4">
        <div class="flex items-center gap-2">
          <span class="p-1.5 rounded-lg bg-red-100 text-red-700">
            <XCircle class="w-5 h-5" />
          </span>
          <div>
            <h3 id="reject-modal-title" class="text-base font-bold text-cortex-text-primary">
              {{ $t('approvals.reject_title', 'Rejeter la Demande') }}
            </h3>
            <p class="text-xs font-mono text-cortex-text-muted mt-0.5">
              {{ requestId }}
            </p>
          </div>
        </div>
        <button
          class="p-2 text-cortex-text-muted hover:text-cortex-text-primary rounded-lg hover:bg-cortex-surface-muted transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Fermer"
          @click="handleClose"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Warning Note -->
      <div class="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-900 flex items-start gap-2">
        <AlertTriangle class="w-4 h-4 shrink-0 text-red-600 mt-0.5" />
        <span>
          Le refus d'approbation bloque l'action sollicitée. Le motif sera notifié au demandeur et gravé dans le journal d'audit.
        </span>
      </div>

      <!-- Reason Textarea -->
      <div class="space-y-2">
        <label for="reject-reason" class="block text-xs font-bold uppercase tracking-wider text-cortex-text-muted">
          {{ $t('approvals.rejection_reason_label', 'Motif obligatoire du refus') }} *
        </label>
        <textarea
          id="reject-reason"
          v-model="reason"
          rows="3"
          class="w-full px-3 py-2.5 rounded-xl border border-cortex-border bg-cortex-surface-muted text-sm text-cortex-text-primary focus:outline-none focus:ring-2 focus:ring-red-500/30 focus:border-red-500 transition-colors"
          :placeholder="$t('approvals.rejection_reason_placeholder', 'Indiquez la justification managériale ou réglementaire du refus...')"
        ></textarea>
        <span v-if="reason.length > 0 && reason.trim().length < 3" class="text-[11px] text-red-600">
          Le motif doit comporter au moins 3 caractères.
        </span>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800">
        {{ errorMessage }}
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3 pt-3 border-t border-cortex-border">
        <button
          type="button"
          class="px-4 py-2.5 rounded-xl border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-xs font-semibold text-cortex-text-secondary transition-colors min-h-[44px]"
          @click="handleClose"
        >
          Annuler
        </button>
        <button
          type="button"
          class="px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold shadow transition-colors min-h-[44px] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="isSubmitting || reason.trim().length < 3"
          @click="handleSubmit"
        >
          <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
          <span>{{ $t('approvals.confirm_rejection_btn', 'Confirmer le Rejet') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AlertTriangle, Loader2, X, XCircle } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'

const props = defineProps<{
  isOpen: boolean
  requestId: string
  title: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'rejected', reason: string): void
}>()

const reason = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

function handleClose() {
  reason.value = ''
  errorMessage.value = ''
  emit('close')
}

async function handleSubmit() {
  if (reason.value.trim().length < 3) return

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    const client = getCortexApiClient()
    const res = await client.rejectApprovalRequest({
      id: props.requestId,
      reason: reason.value.trim()
    })

    if (res.status === 'completed') {
      emit('rejected', reason.value.trim())
      handleClose()
    } else {
      errorMessage.value = res.errors?.[0]?.message || 'Échec du rejet.'
    }
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur inattendue.'
  } finally {
    isSubmitting.value = false
  }
}
</script>
