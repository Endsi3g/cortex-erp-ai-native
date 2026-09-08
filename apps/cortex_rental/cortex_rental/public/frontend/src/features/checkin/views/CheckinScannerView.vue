<template>
  <ScreenPlaceholderCard
    :screen-id="7"
    title="Check-in — Retour Matériel & Diagnostic"
    route-path="/app/cortex-checkin/:rental"
    priority="P0"
    gate="Gate 2 Demo-Critical"
    primary-role="Retour matériel item par item, retours partiels, anomalie 1-clic (manquant/bris/quarantaine)"
    description="Interface de retour d'inventaire et de contrôle qualité. Gestion fluide des retours partiels (avec maintien du reliquat hors-location), déclencheur d'anomalies en 1 clic (marquage manquant, signalement de bris avec téléversement de photos de preuve hashées SHA-256) et diff récapitulatif avant clôture."
    required-permission="cortex:checkin:perform"
    icon-name="LogIn"
  >
    <!-- Anomaly Trigger Bar Preview -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface space-y-3">
      <span class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider block">
        Déclencheurs d'Anomalies 1-Clic
      </span>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <button class="p-3 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 font-semibold hover:bg-amber-100 transition-colors text-left flex items-center justify-between">
          <span>📦 Marquer Élément Manquant</span>
          <span class="text-[10px] font-mono bg-amber-200 px-1.5 py-0.5 rounded">1-Clic</span>
        </button>
        <button class="p-3 rounded-xl border border-red-300 bg-red-50 text-red-900 font-semibold hover:bg-red-100 transition-colors text-left flex items-center justify-between">
          <span>📷 Déclarer Dommage & Photo</span>
          <span class="text-[10px] font-mono bg-red-200 px-1.5 py-0.5 rounded">UploadIntent</span>
        </button>
        <button class="p-3 rounded-xl border border-purple-300 bg-purple-50 text-purple-900 font-semibold hover:bg-purple-100 transition-colors text-left flex items-center justify-between">
          <span>🔬 Mettre en Quarantaine</span>
          <span class="text-[10px] font-mono bg-purple-200 px-1.5 py-0.5 rounded">Maintenance</span>
        </button>
      </div>
    </div>
  </ScreenPlaceholderCard>
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
