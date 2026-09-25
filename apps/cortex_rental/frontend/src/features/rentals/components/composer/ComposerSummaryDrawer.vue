<template>
  <div class="rounded-xl border border-cortex-border bg-cortex-surface p-4 shadow-2xs space-y-3 sticky top-4" data-test="composer-summary-drawer">
    <div class="flex items-center justify-between border-b border-cortex-border pb-2">
      <h4 class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
        Synthèse Devis
      </h4>
      <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cortex-primary-100 text-cortex-primary-800 font-bold">
        7j = 3j Actif
      </span>
    </div>

    <div class="space-y-2 text-xs">
      <div class="flex items-center justify-between text-cortex-text-secondary">
        <span>Client :</span>
        <span class="font-semibold text-cortex-text-primary truncate max-w-[140px]">
          {{ customerName || 'Non sélectionné' }}
        </span>
      </div>

      <div class="flex items-center justify-between text-cortex-text-secondary">
        <span>Période :</span>
        <span class="font-mono text-cortex-text-primary">
          {{ startsAt && endsAt ? `${formatDate(startsAt)} → ${formatDate(endsAt)}` : 'Non définie' }}
        </span>
      </div>

      <div class="flex items-center justify-between text-cortex-text-secondary">
        <span>Jours :</span>
        <span class="font-mono text-cortex-text-primary">
          {{ calendarDays }}j cal. / <strong>{{ billableDays }}j facturés</strong>
        </span>
      </div>

      <div class="flex items-center justify-between text-cortex-text-secondary">
        <span>Équipements :</span>
        <span class="font-semibold text-cortex-text-primary">
          {{ totalItems }} unité(s)
        </span>
      </div>

      <div class="pt-2 border-t border-cortex-border flex items-center justify-between text-sm font-bold text-cortex-text-primary">
        <span>Total TTC :</span>
        <span class="font-mono text-cortex-primary-700 font-bold text-base" data-test="summary-drawer-total">
          {{ formatCurrency(grandTotal) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { calculateBillableDays } from '@/api/mock/MockCortexApiClient'

const props = defineProps<{
  customerName?: string
  startsAt?: string
  endsAt?: string
  totalItems: number
  subtotal: number
}>()

const calendarDays = computed(() => {
  if (!props.startsAt || !props.endsAt) return 7
  const start = new Date(props.startsAt)
  const end = new Date(props.endsAt)
  const diffTime = Math.abs(end.getTime() - start.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return diffDays > 0 ? diffDays : 1
})

const billableDays = computed(() => {
  return calculateBillableDays(calendarDays.value)
})

const grandTotal = computed(() => {
  const taxes = props.subtotal * 0.14975
  return props.subtotal + taxes
})

const formatDate = (d: string) => {
  try {
    const date = new Date(d)
    return `${date.getDate()}/${date.getMonth() + 1}`
  } catch {
    return d
  }
}

const formatCurrency = (amt: number) => {
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
}
</script>
