<template>
  <ScreenPlaceholderCard
    :screen-id="21"
    title="Rental Policies — Politiques Tarifaires & Règles"
    route-path="/app/cortex-rental-policy"
    priority="P2"
    gate="Gate 5 Polish & Final Deliverables"
    primary-role="Consultation des politiques tarifaires et de disponibilité versionnées"
    description="Consultation en lecture seule des règles métier de location : coefficients de durée (7j=3j, 30j=10j), conditions de dépôt de garantie, politiques de franchise d'assurance et règles d'accessoires obligatoires."
    required-permission="cortex:policies:view"
    icon-name="Scale"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
