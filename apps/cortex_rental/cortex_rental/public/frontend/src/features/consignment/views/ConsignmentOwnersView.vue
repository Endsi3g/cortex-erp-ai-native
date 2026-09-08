<template>
  <ScreenPlaceholderCard
    :screen-id="13"
    title="Consignment Owners — Répertoire des Propriétaires"
    route-path="/app/cortex-consignment-owner"
    priority="P1"
    gate="Gate 4 Catalog, Audit & Migration"
    primary-role="Répertoire des propriétaires tiers de consignation et conditions financières"
    description="Annuaire des partenaires tiers déposant du matériel en consignation dans le parc de location. Gestion des coordonnées, contrats cadres, taux de partage de revenus par défaut et inventaire rattaché."
    required-permission="cortex:consignment:view"
    icon-name="Users"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
