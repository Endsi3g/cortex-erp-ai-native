<template>
  <div class="space-y-4 text-xs" data-test="tab-finance-pnl">
    <!-- 7j = 3j Formula Card -->
    <div class="p-4 rounded-xl border border-cortex-primary-300 bg-cortex-primary-50/40 shadow-2xs space-y-2">
      <div class="flex items-center justify-between">
        <h3 class="font-bold text-cortex-primary-950 uppercase tracking-wider text-[11px]">
          Règle Tarifaire Cortex — 7j = 3j
        </h3>
        <span class="px-2 py-0.5 rounded bg-cortex-primary-200 text-cortex-primary-900 font-mono text-[11px] font-bold">
          7 jours calendaires = 3 jours facturés
        </span>
      </div>
      <p class="text-cortex-primary-900 text-[11px]">
        Pour cette location de {{ rental.calendar_days }} jours calendaires, la formule par paliers attribue
        <strong>{{ rental.billable_days }} jours facturables</strong>. Chaque semaine complète de 7 jours est facturée 3 jours, garantissant un ratio attractif pour les productions de cinéma et de séries.
      </p>
    </div>

    <!-- P&L Financial Summary Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Itemized Invoicing Card -->
      <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3">
        <h4 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px] border-b border-cortex-border pb-2">
          Facturation Client (TTC)
        </h4>

        <div class="space-y-2">
          <div class="flex items-center justify-between text-cortex-text-secondary">
            <span>Sous-total HT des équipements :</span>
            <span class="font-mono font-semibold">{{ formatCurrency(rental.subtotal) }}</span>
          </div>
          <div class="flex items-center justify-between text-cortex-text-secondary">
            <span>Remises commerciales accordées :</span>
            <span class="font-mono font-semibold">{{ formatCurrency(rental.discount_total || 0) }}</span>
          </div>
          <div class="flex items-center justify-between text-cortex-text-secondary">
            <span>Taxes combinées (TPS + TVQ 14.975%) :</span>
            <span class="font-mono font-semibold">{{ formatCurrency(rental.tax_amount) }}</span>
          </div>
          <div class="pt-2 border-t border-cortex-border flex items-center justify-between text-sm font-bold text-cortex-text-primary">
            <span>Grand Total Client :</span>
            <span class="font-mono text-cortex-primary-800 text-base" data-test="finance-grand-total">
              {{ formatCurrency(rental.grand_total) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Consignment Share & Cortex Gross Margin -->
      <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3">
        <h4 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px] border-b border-cortex-border pb-2">
          Répartition Marge & Consignation
        </h4>

        <div class="space-y-2">
          <div class="flex items-center justify-between text-cortex-text-secondary">
            <span>Revenu Net Admissible :</span>
            <span class="font-mono font-semibold">{{ formatCurrency(rental.subtotal) }}</span>
          </div>
          <div class="flex items-center justify-between text-amber-900">
            <span>Part Reversements Propriétaires (Consignation) :</span>
            <span class="font-mono font-bold">{{ formatCurrency(estimatedConsignmentShare) }}</span>
          </div>
          <div class="flex items-center justify-between text-cortex-primary-900">
            <span>Marge Brute Cortex Location :</span>
            <span class="font-mono font-bold">{{ formatCurrency(cortexGrossMargin) }}</span>
          </div>
          <div class="pt-2 border-t border-cortex-border flex items-center justify-between text-xs text-cortex-text-muted">
            <span>Ratio de Marge Brute :</span>
            <span class="font-mono font-bold text-cortex-text-primary">
              {{ Math.round((cortexGrossMargin / (rental.subtotal || 1)) * 100) }} %
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RentalTransaction } from '@/types/rental'

const props = defineProps<{
  rental: RentalTransaction
}>()

const estimatedConsignmentShare = computed(() => {
  return props.rental.items
    .filter(i => i.is_consigned)
    .reduce((sum, i) => sum + i.subtotal * 0.70, 0)
})

const cortexGrossMargin = computed(() => {
  return Math.max(0, props.rental.subtotal - estimatedConsignmentShare.value)
})

const formatCurrency = (amt: number) => {
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
}
</script>
