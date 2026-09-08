<template>
  <ScreenPlaceholderCard
    :screen-id="10"
    title="Equipment Detail — Fiche Équipement"
    route-path="/app/cortex-equipment/:item"
    priority="P1"
    gate="Gate 4 Catalog, Audit & Migration"
    primary-role="Fiche équipement, profil location, accessoires requis/optionnels, mini-timeline"
    description="Fiche technique et opérationnelle d'un équipement. Définition du profil de location, règles d'accessoires dépendants (batteries, tiges, plaques), mini-timeline de disponibilité à 14 jours et liste des numéros de série enregistrés."
    required-permission="cortex:catalog:view"
    icon-name="PackageSearch"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
