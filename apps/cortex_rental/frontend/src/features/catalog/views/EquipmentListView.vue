<template>
  <ScreenPlaceholderCard
    :screen-id="9"
    title="Equipment List — Catalogue d'Équipements"
    route-path="/equipment"
    priority="P1"
    gate="Gate 4 Catalog, Audit & Migration"
    primary-role="Catalogue d'équipements louables sérialisés et par quantité"
    description="Répertoire de la flotte d'équipements de cinéma, broadcast, éclairage et sonorisation. Vue par profil de location (Caméras, Optiques, Éclairage, Grip), gestion du suivi sérialisé ou quantitatif, accessoires requis/optionnels et taux journaliers standards."
    required-permission="cortex:catalog:view"
    icon-name="Package"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
