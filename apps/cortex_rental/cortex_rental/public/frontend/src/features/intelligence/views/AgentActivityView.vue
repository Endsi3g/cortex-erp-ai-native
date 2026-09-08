<template>
  <ScreenPlaceholderCard
    :screen-id="18"
    title="Agent Activity — Télémétrie & Traces IA"
    route-path="/app/cortex-agent-activity"
    priority="P1"
    gate="Gate 3 Intake & Intelligence"
    primary-role="Suivi administrateur des runs agents, outils appelés, latences, modèles et coûts"
    description="Cockpit d'observabilité dédié aux administrateurs pour inspecter l'activité des agents Onyx (Intake, Availability, Consignment), les outils FastMCP invoqués, les traces d'exécution, la latence par appel et la consommation de tokens."
    required-permission="cortex:telemetry:admin"
    icon-name="Activity"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
