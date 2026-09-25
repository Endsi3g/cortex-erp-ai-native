<template>
  <ScreenPlaceholderCard
    :screen-id="24"
    title="Audit Log — Journal d'Audit Immuable"
    route-path="/admin/audit"
    priority="P1"
    gate="Gate 4 Catalog, Audit & Migration"
    primary-role="Journal append-only immuable, vue opérationnelle et diff technique JSON"
    description="Journal immuable de toutes les mutations système. Présente une vue opérationnelle en langage naturel pour les gestionnaires et une bascule vers le diff technique JSON (request_id, compte de service, version de policy, hash SHA-256 de preuve)."
    required-permission="cortex:audit:view"
    icon-name="History"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
