<template>
  <ScreenPlaceholderCard
    :screen-id="12"
    title="Kits & Accessories — Packages & Compositions"
    route-path="/app/cortex-kits"
    priority="P2"
    gate="Gate 5 Polish & Final Deliverables"
    primary-role="Composition de packages et kits sans doublon d'inventaire physique"
    description="Gestion des ensembles et packages complets (ex: Kit Caméra A, Kit Lumière Interview). Permet d'assembler des profils d'accessoires et sous-équipements sans créer de doublon d'inventaire physique."
    required-permission="cortex:catalog:manage"
    icon-name="Layers"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
