<template>
  <ScreenPlaceholderCard
    :screen-id="20"
    title="Full Assistant — Espace Conversationnel Étendu"
    route-path="/assistant"
    priority="P2"
    gate="Gate 5 Polish & Final Deliverables"
    primary-role="Espace conversationnel plein écran, multi-contexte, preuves et audit"
    description="Interface conversationnelle étendue avec Onyx pour les requêtes complexes d'analyse d'inventaire, d'optimisation tarifaire ou de planification de projets de tournage d'envergure. Supporte l'épinglage multi-entités et la traçabilité intégrale."
    required-permission="cortex:copilot:access"
    icon-name="MessageSquareCode"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
