<template>
  <div class="space-y-6 max-w-5xl mx-auto" data-test="screen-checkout-scanner">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-cortex-border">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-xl font-bold text-cortex-text-primary tracking-tight">
            {{ t('checkout.title') }}
          </h1>
          <span class="px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 text-[11px] font-semibold">
            Entrepôt & Scanner
          </span>
          <span class="px-2 py-0.5 rounded-full bg-cortex-surface-secondary border border-cortex-border text-cortex-text-muted text-[11px] font-mono">
            Cadence Rapide
          </span>
        </div>
        <p class="text-xs text-cortex-text-secondary mt-1">
          Validation physique du matériel sortant avec cadence rapide (autofocus 52px) et retour sonore/haptique.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <RouterLink
          :to="`/app/cortex-rental/${rentalId}`"
          class="cx-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 min-h-[44px]"
        >
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>Fiche 360°</span>
        </RouterLink>
      </div>
    </div>

    <!-- Error Banner -->
    <CortexErrorBanner
      v-if="errorMessage"
      :error-message="errorMessage"
      @retry="loadRental"
    />

    <!-- Loading Skeleton -->
    <div v-if="isLoading" class="p-6 bg-cortex-surface rounded-xl border border-cortex-border space-y-4">
      <CortexSkeleton :lines="6" />
    </div>

    <div v-else-if="rental" class="space-y-5">
      <!-- Rental Context Banner -->
      <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="space-y-0.5">
          <div class="flex items-center gap-2">
            <span class="font-mono font-bold text-sm text-cortex-primary-700">{{ rental.name }}</span>
            <CortexBadge :state="rental.rental_state === 'Checked Out' ? 'checked_out' : 'contract'" size="sm" />
          </div>
          <span class="text-xs font-semibold text-cortex-text-primary block">{{ rental.customer_name }}</span>
          <span v-if="rental.project_name" class="text-[11px] text-cortex-text-muted block">{{ rental.project_name }}</span>
        </div>

        <div class="flex items-center gap-4 text-xs">
          <div class="text-right">
            <span class="text-[10px] uppercase font-semibold text-cortex-text-muted block">Progression scan</span>
            <span class="font-mono font-bold text-sm text-cortex-text-primary" data-test="checkout-scan-progress">
              {{ scannedSerials.length }} / {{ totalSerialsCount }} scanné(s)
            </span>
          </div>
          <div class="w-20 h-2 rounded-full bg-cortex-surface-secondary overflow-hidden border border-cortex-border">
            <div
              class="h-full bg-cortex-primary-600 transition-all duration-300"
              :style="{ width: `${scanProgressPercent}%` }"
            />
          </div>
        </div>
      </div>

      <!-- Checkout Completed Celebration Banner -->
      <div
        v-if="isCompleted || rental.rental_state === 'Checked Out'"
        class="p-4 rounded-xl border-2 border-cortex-primary-500 bg-cortex-primary-50 text-xs text-cortex-primary-950 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs"
        data-test="checkout-completed-banner"
      >
        <div class="flex items-center gap-2.5">
          <CheckCircle2 class="w-6 h-6 text-cortex-primary-700 flex-shrink-0" />
          <div>
            <strong class="font-bold text-sm block text-cortex-primary-950">{{ t('checkout.checkout_success') }}</strong>
            <span>Le statut de la location a muté vers "Checked Out". L'événement d'audit a été enregistré.</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <RouterLink
            :to="`/app/cortex-checkin/${rental.name}`"
            class="cx-btn-primary text-xs px-3.5 py-2 min-h-[44px] flex items-center gap-1.5 whitespace-nowrap shadow-xs"
            data-test="checkout-to-checkin-link"
          >
            <span>Passer au Check-in (Retour)</span>
            <LogIn class="w-4 h-4" />
          </RouterLink>
        </div>
      </div>

      <!-- 52px Persistent Autofocus Scanner Input -->
      <div class="p-4 rounded-xl border-2 border-cortex-primary-500 bg-cortex-surface shadow-2xs space-y-3" data-test="scanner-section">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold text-cortex-primary-800 uppercase tracking-wider flex items-center gap-1.5">
            <Barcode class="w-4 h-4 text-cortex-primary-600" />
            Scanner Code-barres / Séries
          </span>
          <span class="text-[11px] font-mono text-cortex-text-muted">
            Champ 52px • Autofocus actif
          </span>
        </div>

        <CortexScannerInput
          v-model="barcodeInputValue"
          :auto-focus="true"
          :placeholder="t('checkout.scan_placeholder')"
          :feedback-status="scannerFeedbackStatus"
          :status-message="scannerStatusMessage"
          data-test="checkout-scanner-input"
          @scan="handleBarcodeScan"
        />

        <!-- Inline Warning / Error alerts for Duplicate or Unknown scans -->
        <div
          v-if="duplicateWarning"
          class="p-2.5 rounded-lg border border-amber-300 bg-amber-50 text-xs text-amber-900 flex items-center justify-between"
          data-test="duplicate-barcode-warning"
        >
          <div class="flex items-center gap-2">
            <AlertTriangle class="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>{{ duplicateWarning }}</span>
          </div>
          <button type="button" class="text-amber-800 font-bold hover:underline" @click="duplicateWarning = null">
            Fermer
          </button>
        </div>

        <div
          v-if="unknownBarcodeWarning"
          class="p-2.5 rounded-lg border border-red-300 bg-red-50 text-xs text-red-900 flex items-center justify-between"
          data-test="unknown-barcode-warning"
        >
          <div class="flex items-center gap-2">
            <AlertCircle class="w-4 h-4 text-red-600 flex-shrink-0" />
            <span>{{ unknownBarcodeWarning }}</span>
          </div>
          <button type="button" class="text-red-800 font-bold hover:underline" @click="unknownBarcodeWarning = null">
            Fermer
          </button>
        </div>
      </div>

      <!-- Equipment Items List with Touch Buttons >=44px -->
      <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3" data-test="items-checklist">
        <h3 class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider border-b border-cortex-border pb-2">
          {{ t('checkout.items_to_checkout') }} ({{ rental.items.length }})
        </h3>

        <div class="divide-y divide-cortex-border">
          <div
            v-for="item in rental.items"
            :key="item.id"
            class="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            :data-test="`checkout-item-${item.item_code}`"
          >
            <div class="min-w-0">
              <span class="font-semibold text-xs text-cortex-text-primary block">
                {{ item.item_name }}
              </span>
              <div class="flex items-center gap-2 mt-0.5 text-[11px] text-cortex-text-muted">
                <span class="font-mono text-cortex-primary-700 bg-cortex-primary-50 px-1 rounded">
                  {{ item.item_code }}
                </span>
                <span>Qté : {{ item.quantity }}</span>
              </div>
            </div>

            <!-- Assigned Serials with Scan Status & >=44px Touch Targets -->
            <div class="flex flex-wrap items-center gap-2 justify-end">
              <div
                v-for="sn in item.assigned_serials"
                :key="sn"
                class="flex items-center gap-2 p-1.5 rounded-lg border transition-all"
                :class="scannedSerials.includes(sn) ? 'border-cortex-primary-300 bg-cortex-primary-50/50' : 'border-cortex-border bg-cortex-surface-secondary'"
                :data-test="`serial-chip-${sn}`"
              >
                <div class="flex flex-col text-left pl-1">
                  <span class="font-mono text-xs font-bold text-cortex-text-primary">{{ sn }}</span>
                  <span
                    class="text-[10px] font-semibold"
                    :class="scannedSerials.includes(sn) ? 'text-cortex-primary-700' : 'text-amber-700'"
                  >
                    {{ scannedSerials.includes(sn) ? '✓ ' + t('checkout.scanned') : '○ ' + t('checkout.pending') }}
                  </span>
                </div>

                <!-- Touch target button >=44px -->
                <button
                  type="button"
                  class="min-h-[44px] min-w-[44px] px-2.5 py-1 rounded-md text-xs font-semibold flex items-center justify-center transition-colors focus:outline-none focus:ring-1 focus:ring-cortex-primary-500"
                  :class="scannedSerials.includes(sn)
                    ? 'bg-cortex-primary-100 text-cortex-primary-800 hover:bg-cortex-primary-200'
                    : 'bg-cortex-primary-600 text-white hover:bg-cortex-primary-700 shadow-xs'"
                  :data-test="`touch-scan-btn-${sn}`"
                  @click="handleBarcodeScan({ raw: sn, trimmed: sn })"
                >
                  <span v-if="scannedSerials.includes(sn)">Re-scan</span>
                  <span v-else>Scanner</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Completion Footer -->
      <div class="pt-2 flex items-center justify-between gap-3">
        <RouterLink
          :to="`/app/cortex-rental/${rental.name}`"
          class="cx-btn-secondary text-xs px-4 py-2.5 min-h-[44px] flex items-center gap-1.5"
        >
          <ArrowLeft class="w-4 h-4" />
          <span>Annuler / Retour</span>
        </RouterLink>

        <button
          type="button"
          class="cx-btn-primary text-xs px-6 py-2.5 min-h-[44px] flex items-center gap-2 font-bold shadow-md"
          :disabled="scannedSerials.length === 0 || isSubmitting"
          data-test="finalize-checkout-btn"
          @click="finalizeCheckout"
        >
          <CheckCircle2 class="w-4 h-4" />
          <span v-if="isSubmitting">Validation en cours...</span>
          <span v-else>{{ t('checkout.complete_checkout') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, CheckCircle2, Barcode, AlertTriangle, AlertCircle, LogIn } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { RentalTransaction } from '@/types/rental'
import { ScannerFeedback } from '@/utils/scanner'
import CortexScannerInput from '@/design-system/components/base/CortexScannerInput.vue'
import CortexBadge from '@/design-system/components/base/CortexBadge.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'

const { t } = useI18n()
const route = useRoute()

const rentalId = computed(() => String(route.params.rental || ''))

const rental = ref<RentalTransaction | null>(null)
const isLoading = ref<boolean>(false)
const isSubmitting = ref<boolean>(false)
const errorMessage = ref<string | null>(null)

const barcodeInputValue = ref<string>('')
const scannerFeedbackStatus = ref<'idle' | 'success' | 'warning' | 'error'>('idle')
const scannerStatusMessage = ref<string>('')
const duplicateWarning = ref<string | null>(null)
const unknownBarcodeWarning = ref<string | null>(null)
const isCompleted = ref<boolean>(false)

const scannedSerials = ref<string[]>([])

const allAssignedSerials = computed<string[]>(() => {
  if (!rental.value) return []
  return rental.value.items.flatMap(i => i.assigned_serials || [])
})

const totalSerialsCount = computed(() => allAssignedSerials.value.length)

const scanProgressPercent = computed(() => {
  if (totalSerialsCount.value === 0) return 0
  return Math.round((scannedSerials.value.length / totalSerialsCount.value) * 100)
})

const loadRental = async () => {
  isLoading.value = true
  errorMessage.value = null
  try {
    const client = getCortexApiClient()
    const res = await client.getRental({ id: rentalId.value })
    rental.value = res

    // Restore any existing scanned serials
    const existing = res.items.flatMap(i => i.scanned_checkout_serials || [])
    scannedSerials.value = [...new Set(existing)]

    // If state is already Checked Out
    if (res.rental_state === 'Checked Out') {
      isCompleted.value = true
    }
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors du chargement de la location'
  } finally {
    isLoading.value = false
  }
}

const handleBarcodeScan = async (payload: { raw: string; trimmed: string }) => {
  const barcode = payload.trimmed
  duplicateWarning.value = null
  unknownBarcodeWarning.value = null

  // 1. Check Duplicate
  if (scannedSerials.value.includes(barcode)) {
    ScannerFeedback.playError()
    scannerFeedbackStatus.value = 'warning'
    scannerStatusMessage.value = t('checkout.duplicate_barcode')
    duplicateWarning.value = `Le numéro de série ${barcode} a déjà été validé pour cette sortie !`
    return
  }

  // 2. Check Unknown / Not assigned
  if (!allAssignedSerials.value.includes(barcode)) {
    ScannerFeedback.playError()
    scannerFeedbackStatus.value = 'error'
    scannerStatusMessage.value = t('checkout.unknown_barcode')
    unknownBarcodeWarning.value = `Le code ${barcode} n'est pas assigné à ce contrat (${rental.value?.name}).`
    return
  }

  // A scan only becomes successful after the server confirms the mutation.
  try {
    const client = getCortexApiClient()
    if (rental.value) {
      const result = await client.scanCheckoutSerial({
        rental_id: rental.value.id,
        serial_number: barcode
      })
      if (result.status !== 'completed') {
        ScannerFeedback.playError()
        scannerFeedbackStatus.value = 'error'
        scannerStatusMessage.value = result.errors?.[0]?.message || 'Le serveur a refusé le scan.'
        return
      }
      scannedSerials.value.push(barcode)
      ScannerFeedback.playSuccess()
      scannerFeedbackStatus.value = 'success'
      scannerStatusMessage.value = `Numéro de série ${barcode} validé par le serveur.`
    }
  } catch (err: unknown) {
    ScannerFeedback.playError()
    scannerFeedbackStatus.value = 'error'
    scannerStatusMessage.value = err instanceof Error ? err.message : 'Impossible d’enregistrer ce scan.'
  }
}

const finalizeCheckout = async () => {
  if (!rental.value || isSubmitting.value) return
  isSubmitting.value = true
  errorMessage.value = null

  try {
    const client = getCortexApiClient()
    const res = await client.completeCheckout({
      rental_id: rental.value.id
    })

    if (res.status === 'completed') {
      rental.value.rental_state = 'Checked Out'
      isCompleted.value = true
      ScannerFeedback.playSuccess()
    } else if (res.status === 'policy_denied') {
      errorMessage.value = res.policy_result?.explanation || 'Sortie refusée par policy.'
    }
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors de la finalisation du check-out'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  loadRental()
})
</script>
