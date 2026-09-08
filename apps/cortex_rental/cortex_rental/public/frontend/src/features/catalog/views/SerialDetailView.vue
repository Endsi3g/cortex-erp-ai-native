<template>
  <ScreenPlaceholderCard
    :screen-id="11"
    title="Serial Number Detail — Passeport Unitaire"
    route-path="/app/cortex-serial/:serial"
    priority="P1"
    gate="Gate 4 Catalog, Audit & Migration"
    primary-role="Fiche sérialisée, propriétaire tiers, taux consignation, maintenance append-only"
    description="Passeport unitaire d'un numéro de série physique. Identification du propriétaire légal (interne vs consignation tiers), taux de reversement propriétaire sans fuite locataire, statut de disponibilité actuel et historique immuable des maintenances et réparations."
    required-permission="cortex:serial:view"
    icon-name="Barcode"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
