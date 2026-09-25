<template>
  <ScreenPlaceholderCard
    :screen-id="16"
    title="Incoming Requests — Demandes Entrantes IA"
    route-path="/ai/incoming"
    priority="P1"
    gate="Gate 3 Intake & Intelligence"
    primary-role="Révision des demandes e-mail/PDF extraites par IA avec score de confiance et conversion"
    description="File d'attente d'ingestion structurée des e-mails, devis PDF et formulaires entrants traités par l'agent Cortex Intake. Affiche le score de confiance par champ, surligne les données manquantes et offre la conversion 1-clic en devis dans le Composer."
    required-permission="cortex:intake:view"
    icon-name="Inbox"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
