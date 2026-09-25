<template>
  <ScreenPlaceholderCard
    :screen-id="23"
    title="Import & Migration — Assistant de Migration Legacy"
    route-path="/admin/import"
    priority="P1"
    gate="Gate 4 Catalog, Audit & Migration"
    primary-role="Assistant d'importation legacy 6 étapes (quarantaine, mapping, preview, rollback)"
    description="Assistant structuré en 6 étapes pour l'ingestion des bases legacy (RentalDesk, Current RMS, EasyJob, Excel) : téléversement, mise en quarantaine, mappage des champs, aperçu des écarts, validation et exécution avec capacité de rollback."
    required-permission="cortex:migration:run"
    icon-name="UploadCloud"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
