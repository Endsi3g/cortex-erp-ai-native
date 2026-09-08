<template>
  <ScreenPlaceholderCard
    :screen-id="14"
    title="Consignment Dashboard — Suivi des Reversements"
    route-path="/app/cortex-consignment"
    priority="P0"
    gate="Gate 2 Demo-Critical"
    primary-role="Dashboard de consignation, revenus nets admissibles et montants dus aux propriétaires"
    description="Tableau de bord financier pour le calcul et le suivi des reversements dus aux propriétaires tiers de matériel. Agrégation automatique à partir des snapshots de facturation et génération des relevés étanches sans fuite de données locataire."
    required-permission="cortex:consignment:view"
    icon-name="Percent"
  >
    <!-- Consignment Metrics Preview -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
      <div class="p-3.5 rounded-xl border border-cortex-border bg-cortex-surface">
        <span class="text-cortex-text-muted font-medium">Revenu Net Admissible (Mois)</span>
        <span class="text-xl font-bold text-cortex-ink-900 font-mono block mt-1">42 850,00 $</span>
      </div>
      <div class="p-3.5 rounded-xl border border-cortex-border bg-cortex-surface">
        <span class="text-cortex-text-muted font-medium">Montant Dû aux Propriétaires</span>
        <span class="text-xl font-bold text-cortex-primary-700 font-mono block mt-1">29 995,00 $</span>
      </div>
      <div class="p-3.5 rounded-xl border border-cortex-border bg-cortex-surface">
        <span class="text-cortex-text-muted font-medium">Séries Actives en Consignation</span>
        <span class="text-xl font-bold text-cortex-ink-900 font-mono block mt-1">14 unités</span>
      </div>
    </div>
  </ScreenPlaceholderCard>
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
