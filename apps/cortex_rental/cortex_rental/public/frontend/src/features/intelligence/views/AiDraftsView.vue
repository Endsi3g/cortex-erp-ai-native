<template>
  <ScreenPlaceholderCard
    :screen-id="17"
    title="AI Drafts — Hub des Propositions IA"
    route-path="/app/cortex-ai-drafts"
    priority="P1"
    gate="Gate 3 Intake & Intelligence"
    primary-role="Centralisation des brouillons IA non validés, édition, rejet avec motif"
    description="Tableau de bord centralisant toutes les propositions, devis préliminaires et suggestions d'accessoires préparées par les agents Onyx. Permet la révision, l'édition dans le workflow approprié, la soumission à approbation ou le rejet avec motif évaluatif."
    required-permission="cortex:drafts:review"
    icon-name="Sparkles"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
