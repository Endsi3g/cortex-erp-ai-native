<template>
  <div class="space-y-5" data-test="step-review-create">
    <!-- Readiness Assessment Box -->
    <div
      class="p-4 rounded-xl border bg-cortex-surface shadow-2xs space-y-3"
      :class="isReadyForContract ? 'border-cortex-border' : 'border-amber-300 bg-amber-50/20'"
    >
      <div class="flex items-center justify-between">
        <h3 class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          Évaluation Préalable de Readiness
        </h3>
        <span
          class="px-2 py-0.5 rounded text-[10px] font-bold"
          :class="isReadyForContract ? 'bg-cortex-primary-100 text-cortex-primary-800' : 'bg-amber-100 text-amber-900'"
        >
          {{ isReadyForContract ? '✓ Prêt pour Contrat' : '⚠ Approbation requise pour Contrat' }}
        </span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
        <div class="p-2.5 rounded-lg border border-cortex-border bg-cortex-surface-secondary flex items-center justify-between">
          <span>Compte Client :</span>
          <span class="font-bold text-cortex-primary-700">Validé</span>
        </div>
        <div class="p-2.5 rounded-lg border border-cortex-border bg-cortex-surface-secondary flex items-center justify-between">
          <span>Assurance :</span>
          <span class="font-bold" :class="isInsuranceExpired ? 'text-red-600' : 'text-cortex-primary-700'">
            {{ isInsuranceExpired ? 'Expirée' : 'Conforme' }}
          </span>
        </div>
        <div class="p-2.5 rounded-lg border border-cortex-border bg-cortex-surface-secondary flex items-center justify-between">
          <span>Dépôt / Solvabilité :</span>
          <span class="font-bold text-cortex-primary-700">Validé</span>
        </div>
      </div>
    </div>

    <!-- Review Summary Card -->
    <div class="p-5 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-4">
      <h3 class="text-sm font-bold text-cortex-text-primary border-b border-cortex-border pb-2">
        Récapitulatif de la Transaction
      </h3>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
        <div>
          <span class="text-cortex-text-muted block text-[10px] uppercase font-semibold">Client</span>
          <span class="font-bold text-cortex-text-primary">{{ step1.customerName }}</span>
          <span class="text-cortex-text-muted block text-[11px]">{{ step1.customerEmail }}</span>
        </div>

        <div>
          <span class="text-cortex-text-muted block text-[10px] uppercase font-semibold">Période & Projet</span>
          <span class="font-mono text-cortex-text-primary">{{ step1.startsAt }} → {{ step1.endsAt }}</span>
          <span class="text-cortex-text-secondary block text-[11px]">{{ step1.projectName || 'Projet sans nom' }}</span>
        </div>
      </div>

      <!-- Line items summary -->
      <div class="border-t border-cortex-border pt-3 space-y-2">
        <span class="text-cortex-text-muted block text-[10px] uppercase font-semibold">
          Équipements & Séries assignées ({{ lines.length }})
        </span>
        <div
          v-for="line in lines"
          :key="line.itemCode"
          class="flex items-center justify-between text-xs py-1 border-b border-cortex-border/50 last:border-b-0"
        >
          <div>
            <span class="font-semibold text-cortex-text-primary">{{ line.quantity }}× {{ line.itemName }}</span>
            <div v-if="line.assignedSerials.length > 0" class="flex items-center gap-1 mt-0.5">
              <span class="text-[10px] text-cortex-text-muted font-mono">
                Séries: {{ line.assignedSerials.join(', ') }}
              </span>
            </div>
          </div>
          <span class="font-mono font-semibold text-cortex-text-primary">
            {{ formatCurrency(line.dailyRate * line.quantity * billableDays) }}
          </span>
        </div>
      </div>

      <!-- Financial Totals -->
      <div class="border-t border-cortex-border pt-3 space-y-1.5 text-xs">
        <div class="flex items-center justify-between text-cortex-text-secondary">
          <span>Sous-total HT ({{ billableDays }}j facturés) :</span>
          <span class="font-mono font-semibold">{{ formatCurrency(subtotal) }}</span>
        </div>
        <div class="flex items-center justify-between text-cortex-text-secondary">
          <span>Taxes (14.975%) :</span>
          <span class="font-mono font-semibold">{{ formatCurrency(taxAmount) }}</span>
        </div>
        <div class="flex items-center justify-between text-base font-bold text-cortex-text-primary pt-1 border-t border-cortex-border">
          <span>Total TTC (CAD) :</span>
          <span class="font-mono text-cortex-primary-800 text-lg" data-test="review-grand-total">
            {{ formatCurrency(grandTotal) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Error Banner -->
    <div
      v-if="errorMessage"
      class="p-3 rounded-lg border border-red-300 bg-red-50 text-xs text-red-900"
    >
      {{ errorMessage }}
    </div>

    <!-- Actions Bar -->
    <div class="pt-3 border-t border-cortex-border flex flex-col sm:flex-row items-center justify-between gap-3">
      <button
        type="button"
        class="cx-btn-secondary text-xs px-3.5 py-2 flex items-center gap-1.5 w-full sm:w-auto justify-center"
        :disabled="isSubmitting"
        @click="emit('prev')"
      >
        <ArrowLeft class="w-3.5 h-3.5" />
        <span>Précédent : Équipements</span>
      </button>

      <div class="flex items-center gap-2.5 w-full sm:w-auto justify-end">
        <!-- Quote Button (Non-blocking) -->
        <button
          type="button"
          class="cx-btn-secondary text-xs px-4 py-2 border-cortex-primary-600 text-cortex-primary-800 hover:bg-cortex-primary-50 font-semibold"
          :disabled="isSubmitting"
          data-test="create-quote-action-btn"
          @click="openConfirmation('Quote')"
        >
          <span>{{ t('composer.create_quote_btn') }}</span>
        </button>

        <!-- Reservation Button (Blocks inventory) -->
        <button
          type="button"
          class="cx-btn-primary text-xs px-4 py-2 font-semibold"
          :disabled="isSubmitting"
          data-test="confirm-reservation-action-btn"
          @click="openConfirmation('Reservation')"
        >
          <span>{{ t('composer.confirm_reservation_btn') }}</span>
        </button>
      </div>
    </div>

    <!-- Confirmation Modal with Anti Double-Click Protection -->
    <CortexModal
      :model-value="showConfirmModal"
      :title="t('composer.confirm_modal_title')"
      size="sm"
      @close="showConfirmModal = false"
    >
      <div class="space-y-3 text-xs text-cortex-text-secondary" data-test="composer-confirm-modal">
        <p>
          Vous allez enregistrer cette location au statut
          <strong class="text-cortex-text-primary">{{ pendingActionState === 'Quote' ? 'Soumission (Quote)' : 'Réservation' }}</strong>
          pour <strong>{{ step1.customerName }}</strong>.
        </p>
        <div v-if="pendingActionState === 'Reservation'" class="p-2.5 rounded bg-amber-50 border border-amber-200 text-amber-900">
          Cette action bloquera l'inventaire sélectionné pour la période demandée.
        </div>
        <div class="p-2 rounded bg-cortex-surface-secondary font-mono text-[11px] text-cortex-text-muted flex justify-between">
          <span>Idempotency-Key :</span>
          <span class="truncate max-w-[180px]">{{ idempotencyKey }}</span>
        </div>
      </div>

      <template #footer>
        <div class="flex items-center justify-end gap-2">
          <button
            type="button"
            class="cx-btn-secondary text-xs px-3 py-1.5"
            :disabled="isSubmitting"
            @click="showConfirmModal = false"
          >
            Annuler
          </button>
          <button
            type="button"
            class="cx-btn-primary text-xs px-4 py-1.5"
            :disabled="isSubmitting"
            data-test="confirm-modal-submit-btn"
            @click="executeCreation"
          >
            <span v-if="isSubmitting">Enregistrement...</span>
            <span v-else>Confirmer & Enregistrer</span>
          </button>
        </div>
      </template>
    </CortexModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft } from 'lucide-vue-next'
import { generateIdempotencyKey } from '@/utils/idempotency'
import { getCortexApiClient } from '@/api'
import { calculateBillableDays } from '@/api/mock/MockCortexApiClient'
import CortexModal from '@/design-system/components/base/CortexModal.vue'
import type { ComposerStep1Data } from './StepClientDates.vue'
import type { ComposerLineItem } from './StepEquipmentPricing.vue'

const { t } = useI18n()
const router = useRouter()

const props = defineProps<{
  step1: ComposerStep1Data
  lines: ComposerLineItem[]
}>()

const emit = defineEmits<{
  (e: 'prev'): void
}>()

const isSubmitting = ref<boolean>(false)
const errorMessage = ref<string | null>(null)
const showConfirmModal = ref<boolean>(false)
const pendingActionState = ref<'Quote' | 'Reservation'>('Quote')
const idempotencyKey = ref<string>('')

const calendarDays = computed(() => {
  if (!props.step1.startsAt || !props.step1.endsAt) return 7
  const start = new Date(props.step1.startsAt)
  const end = new Date(props.step1.endsAt)
  const diffTime = Math.abs(end.getTime() - start.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return diffDays > 0 ? diffDays : 1
})

const billableDays = computed(() => {
  return calculateBillableDays(calendarDays.value)
})

const subtotal = computed(() => {
  return props.lines.reduce((acc, line) => {
    return acc + line.dailyRate * line.quantity * billableDays.value
  }, 0)
})

const taxAmount = computed(() => {
  return Math.round(subtotal.value * 0.14975 * 100) / 100
})

const grandTotal = computed(() => {
  return subtotal.value + taxAmount.value
})

const isInsuranceExpired = computed(() => {
  return props.step1.customerId === 'DEMO-CUST-003'
})

const isReadyForContract = computed(() => {
  return !isInsuranceExpired.value
})

const openConfirmation = (state: 'Quote' | 'Reservation') => {
  pendingActionState.value = state
  idempotencyKey.value = generateIdempotencyKey()
  showConfirmModal.value = true
}

const executeCreation = async () => {
  if (isSubmitting.value) return // Anti double-click protection
  isSubmitting.value = true
  errorMessage.value = null

  try {
    const client = getCortexApiClient()
    const draftRes = await client.createQuoteDraft({
      customer_id: props.step1.customerId,
      starts_at: `${props.step1.startsAt}T08:00:00Z`,
      ends_at: `${props.step1.endsAt}T18:00:00Z`,
      project_name: props.step1.projectName || undefined,
      notes: props.step1.notes || undefined,
      items: props.lines.map(l => ({
        item_code: l.itemCode,
        quantity: l.quantity
      }))
    })

    const createdId = draftRes.entity_id || 'DEMO-TRX-2026-006'

    if (pendingActionState.value === 'Reservation') {
      await client.requestReservation({
        rental_id: createdId,
        version: 1
      })
    }

    showConfirmModal.value = false
    router.push(`/app/cortex-rental/${createdId}`)
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors de la création de la transaction'
  } finally {
    isSubmitting.value = false
  }
}

const formatCurrency = (amt: number) => {
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
}
</script>
