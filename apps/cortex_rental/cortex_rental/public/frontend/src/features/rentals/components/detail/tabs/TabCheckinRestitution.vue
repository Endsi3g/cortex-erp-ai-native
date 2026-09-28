<template>
  <div data-test="tab-checkin-restitution">
    <div class="flex items-center justify-between gap-3">
      <h3 class="m-0 text-base font-semibold">Avancement de la restitution</h3>
      <RouterLink :to="`/app/cortex-checkin/${rental.name}`" class="cx-btn-soft" data-test="open-scanner-from-tab">Ouvrir le check-in</RouterLink>
    </div>
    <KpiStrip :items="kpis" />
    <p class="m-0 text-sm" style="color: var(--erp-muted)">
      Les comptes viennent des numéros de série scannés à la sortie et au retour. Les manquants, dommages et mises en quarantaine sont enregistrés au check-in: consultez l'onglet Journal d'audit ou l'écran de check-in.
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RentalTransaction } from '@/types/rental'
import KpiStrip, { type KpiItem } from '@/features/common/components/KpiStrip.vue'

const props = defineProps<{ rental: RentalTransaction }>()

const assigned = computed(() => props.rental.items.reduce((sum, i) => sum + (i.assigned_serials?.length ?? 0), 0))
const checkedOut = computed(() => props.rental.items.reduce((sum, i) => sum + i.scanned_checkout_serials.length, 0))
const checkedIn = computed(() => props.rental.items.reduce((sum, i) => sum + i.scanned_checkin_serials.length, 0))
const kpis = computed<KpiItem[]>(() => [
  { key: 'assigned', label: 'Séries assignées', value: String(assigned.value) },
  { key: 'out', label: 'Sorties scannées', value: String(checkedOut.value) },
  { key: 'in', label: 'Retours scannés', value: String(checkedIn.value), positive: true },
  { key: 'open', label: 'Encore dehors', value: String(Math.max(0, checkedOut.value - checkedIn.value)) }
])
</script>
