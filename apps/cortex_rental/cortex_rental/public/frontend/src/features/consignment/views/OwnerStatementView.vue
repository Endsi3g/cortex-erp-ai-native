<template>
  <ScreenPlaceholderCard
    :screen-id="15"
    title="Owner Statement — Relevé Propriétaire Étanche"
    route-path="/app/cortex-owner-statement/:owner/:period"
    priority="P0"
    gate="Gate 2 Demo-Critical"
    primary-role="Relevé propriétaire étanche OwnerStatementSafe (zéro PII locataire, bannière explicite)"
    description="Relevé mensuel certifié à destination du propriétaire tiers. Construit strictement selon le contrat OwnerStatementSafe excluant toute référence ou métadonnée sur les clients locataires, leurs coordonnées, notes ou projets. Export PDF/CSV certifié conforme aux 8 tests de confidentialité."
    required-permission="cortex:consignment:finance"
    icon-name="FileCheck"
  >
    <!-- Mandatory Privacy Banner -->
    <div class="p-3.5 rounded-xl border-2 border-cortex-primary-500 bg-cortex-primary-50 text-xs text-cortex-primary-950 font-medium flex items-center gap-2.5">
      <span class="text-base">🛡️</span>
      <span><strong>Bannière Permanente de Confidentialité :</strong> Informations clients exclues pour la confidentialité des locations.</span>
    </div>
  </ScreenPlaceholderCard>
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
