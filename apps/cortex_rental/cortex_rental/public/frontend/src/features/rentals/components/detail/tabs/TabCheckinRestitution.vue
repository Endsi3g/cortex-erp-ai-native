<template>
  <div class="space-y-4 text-xs" data-test="tab-checkin-restitution">
    <!-- Restitution Progress Overview -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px]">
          État d'Avancement de la Restitution
        </h3>
        <RouterLink
          :to="`/app/cortex-checkin/${rental.name}`"
          class="cx-btn-secondary text-[11px] px-3 py-1.5"
          data-test="open-scanner-from-tab"
        >
          Ouvrir Scanner Check-in →
        </RouterLink>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
        <div class="p-3 rounded-lg bg-cortex-surface-secondary border border-cortex-border text-center">
          <span class="text-[10px] text-cortex-text-muted block">Éléments Sortis</span>
          <span class="text-base font-bold font-mono text-purple-700">{{ totalCheckedOut }}</span>
        </div>
        <div class="p-3 rounded-lg bg-cortex-surface-secondary border border-cortex-border text-center">
          <span class="text-[10px] text-cortex-text-muted block">Restitués Conformes</span>
          <span class="text-base font-bold font-mono text-cortex-primary-700">{{ totalCheckedIn }}</span>
        </div>
        <div class="p-3 rounded-lg bg-cortex-surface-secondary border border-cortex-border text-center">
          <span class="text-[10px] text-cortex-text-muted block">Manquants</span>
          <span class="text-base font-bold font-mono text-red-600">{{ missingCount }}</span>
        </div>
        <div class="p-3 rounded-lg bg-cortex-surface-secondary border border-cortex-border text-center">
          <span class="text-[10px] text-cortex-text-muted block">Quarantaine / Bris</span>
          <span class="text-base font-bold font-mono text-amber-600">{{ damageCount }}</span>
        </div>
      </div>
    </div>

    <!-- Anomaly Log Section -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3">
      <h4 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px]">
        Journal des Anomalies Constatées
      </h4>

      <div v-if="rental.rental_state === 'Partially Returned'" class="space-y-2.5">
        <div class="p-3 rounded-lg border border-amber-300 bg-amber-50/40 flex items-start justify-between gap-3">
          <div>
            <div class="flex items-center gap-1.5 font-bold text-amber-900">
              <span>⚠ Élément Manquant : Adaptateur PL vers LPL</span>
            </div>
            <p class="text-[11px] text-amber-800 mt-0.5">
              Accessoire non présent dans la flight case au déchargement du 1er septembre. Reliquat en attente.
            </p>
          </div>
          <span class="px-2 py-0.5 rounded bg-amber-200 text-amber-950 font-mono text-[10px] font-bold">
            Reliquat actif
          </span>
        </div>

        <div class="p-3 rounded-lg border border-red-300 bg-red-50/40 flex items-start justify-between gap-3">
          <div>
            <div class="flex items-center gap-1.5 font-bold text-red-900">
              <span>● Quarantaine : ARRI Alexa 35 (#DEMO-SN-ALX-004)</span>
            </div>
            <p class="text-[11px] text-red-800 mt-0.5">
              Poussière interne constatée sur le filtre OLPF. Envoyé en maintenance service bench B.
            </p>
          </div>
          <span class="px-2 py-0.5 rounded bg-red-200 text-red-950 font-mono text-[10px] font-bold">
            Service Bench B
          </span>
        </div>
      </div>

      <div v-else class="py-4 text-center text-cortex-text-muted text-xs">
        Aucune anomalie enregistrée sur cette transaction.
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

const totalCheckedOut = computed(() => {
  return props.rental.items.reduce((sum, i) => sum + i.scanned_checkout_serials.length, 0)
})

const totalCheckedIn = computed(() => {
  return props.rental.items.reduce((sum, i) => sum + i.scanned_checkin_serials.length, 0)
})

const missingCount = computed(() => {
  return props.rental.rental_state === 'Partially Returned' ? 1 : 0
})

const damageCount = computed(() => {
  return props.rental.rental_state === 'Partially Returned' ? 1 : 0
})
</script>
