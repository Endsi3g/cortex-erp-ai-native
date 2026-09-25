<template>
  <div class="p-5 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-4" data-test="rental-header-banner">
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
      <!-- Left Info Block -->
      <div class="space-y-1.5">
        <div class="flex flex-wrap items-center gap-2.5">
          <h1 class="text-xl font-bold font-mono text-cortex-text-primary tracking-tight">
            {{ rental.name }}
          </h1>
          <CortexBadge :state="mapStateToBadge(rental.rental_state)" size="md" />
          <span class="px-2 py-0.5 rounded-full bg-cortex-surface-secondary border border-cortex-border text-cortex-text-muted text-[11px] font-mono">
            {{ rental.provenance }}
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-cortex-text-secondary">
          <div class="flex items-center gap-1.5">
            <User class="w-3.5 h-3.5 text-cortex-text-muted" />
            <span class="font-semibold text-cortex-text-primary">{{ rental.customer_name }}</span>
          </div>
          <div v-if="rental.project_name" class="flex items-center gap-1.5">
            <Film class="w-3.5 h-3.5 text-cortex-text-muted" />
            <span>{{ rental.project_name }}</span>
          </div>
          <div class="flex items-center gap-1.5 font-mono">
            <Calendar class="w-3.5 h-3.5 text-cortex-text-muted" />
            <span>{{ formatDateRange(rental.starts_at, rental.ends_at) }}</span>
            <span class="text-cortex-text-muted">({{ rental.billable_days }}j facturés / {{ rental.calendar_days }}j cal.)</span>
          </div>
        </div>
      </div>

      <!-- Right Action & Price Block -->
      <div class="flex items-center gap-4 justify-between lg:justify-end">
        <div class="text-right">
          <span class="text-[10px] uppercase tracking-wider text-cortex-text-muted block font-semibold">Total TTC</span>
          <span class="text-xl font-bold font-mono text-cortex-primary-800" data-test="header-grand-total">
            {{ formatCurrency(rental.grand_total) }}
          </span>
        </div>

        <!-- Guided Next Action CTA -->
        <div>
          <!-- Quote -> Reservation -->
          <button
            v-if="rental.rental_state === 'Quote'"
            type="button"
            class="cx-btn-primary text-xs px-4 py-2 font-semibold shadow-xs"
            :disabled="isActionLoading"
            data-test="cta-confirm-reservation"
            @click="emit('action', 'requestReservation')"
          >
            <CheckCircle2 class="w-4 h-4 mr-1.5" />
            <span>{{ t('rental_detail.next_action_quote') }}</span>
          </button>

          <!-- Reservation -> Contract -->
          <button
            v-else-if="rental.rental_state === 'Reservation'"
            type="button"
            class="cx-btn-primary text-xs px-4 py-2 font-semibold shadow-xs"
            :disabled="isActionLoading"
            data-test="cta-request-contract"
            @click="emit('action', 'requestContract')"
          >
            <ShieldCheck class="w-4 h-4 mr-1.5" />
            <span>{{ t('rental_detail.next_action_reservation') }}</span>
          </button>

          <!-- Contract -> Checkout -->
          <RouterLink
            v-else-if="rental.rental_state === 'Contract'"
            :to="`/checkout/${rental.name}`"
            class="cx-btn-primary text-xs px-4 py-2 font-semibold shadow-xs flex items-center gap-1.5"
            data-test="cta-start-checkout"
          >
            <LogOut class="w-4 h-4" />
            <span>{{ t('rental_detail.next_action_contract') }}</span>
          </RouterLink>

          <!-- Checked Out -> Checkin -->
          <RouterLink
            v-else-if="rental.rental_state === 'Checked Out'"
            :to="`/checkin/${rental.name}`"
            class="cx-btn-primary text-xs px-4 py-2 font-semibold shadow-xs flex items-center gap-1.5"
            data-test="cta-start-checkin"
          >
            <LogIn class="w-4 h-4" />
            <span>{{ t('rental_detail.next_action_checkout') }}</span>
          </RouterLink>

          <!-- Partially Returned -> Continue Checkin -->
          <RouterLink
            v-else-if="rental.rental_state === 'Partially Returned'"
            :to="`/checkin/${rental.name}`"
            class="cx-btn-secondary text-xs px-4 py-2 font-semibold shadow-xs flex items-center gap-1.5 border-amber-400 bg-amber-50 text-amber-900 hover:bg-amber-100"
            data-test="cta-continue-checkin"
          >
            <LogIn class="w-4 h-4" />
            <span>{{ t('rental_detail.next_action_partial') }}</span>
          </RouterLink>

          <!-- Invoiced -->
          <div
            v-else-if="rental.rental_state === 'Invoiced'"
            class="px-3 py-1.5 rounded-lg bg-cortex-surface-secondary border border-cortex-border text-xs font-semibold text-cortex-text-primary flex items-center gap-1.5"
          >
            <CheckCircle2 class="w-4 h-4 text-cortex-primary-600" />
            <span>{{ t('rental_detail.next_action_invoiced') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { User, Film, Calendar, CheckCircle2, ShieldCheck, LogOut, LogIn } from 'lucide-vue-next'
import type { RentalTransaction, RentalState } from '@/types/rental'
import CortexBadge from '@/design-system/components/base/CortexBadge.vue'

const { t } = useI18n()

defineProps<{
  rental: RentalTransaction
  isActionLoading?: boolean
}>()

const emit = defineEmits<{
  (e: 'action', actionName: string): void
}>()

const mapStateToBadge = (state: RentalState) => {
  switch (state) {
    case 'Quote': return 'quote'
    case 'Reservation': return 'reservation'
    case 'Contract': return 'contract'
    case 'Checked Out': return 'checked_out'
    case 'Partially Returned': return 'partial_return'
    case 'Returned': return 'returned'
    case 'Invoiced': return 'invoiced'
    case 'Cancelled': return 'cancelled'
    default: return 'draft'
  }
}

const formatDateRange = (startsAt: string, endsAt: string) => {
  try {
    const s = new Date(startsAt)
    const e = new Date(endsAt)
    return `${s.getDate()}/${s.getMonth() + 1} → ${e.getDate()}/${e.getMonth() + 1}/${e.getFullYear()}`
  } catch {
    return `${startsAt} → ${endsAt}`
  }
}

const formatCurrency = (amt: number) => {
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
}
</script>
