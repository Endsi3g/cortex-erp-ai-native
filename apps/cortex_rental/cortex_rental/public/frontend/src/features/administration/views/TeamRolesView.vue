<template>
  <ScreenPlaceholderCard
    :screen-id="22"
    title="Team & Roles — Permissions & Comptes de Service"
    route-path="/app/cortex-team"
    priority="P2"
    gate="Gate 5 Polish & Final Deliverables"
    primary-role="Matrice des permissions par rôle et identification des comptes de service"
    description="Visualisation de la matrice des permissions par rôle opérationnel (Directeur d'opérations, Responsable comptoir, Technicien entrepôt, Gestionnaire financier) et suivi des comptes de service dédiés aux intégrations et agents IA."
    required-permission="cortex:team:manage"
    icon-name="ShieldAlert"
  />
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
