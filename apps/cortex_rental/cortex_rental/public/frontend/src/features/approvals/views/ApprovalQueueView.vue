<template>
  <ScreenPlaceholderCard
    :screen-id="8"
    title="Approval Queue — SAS d'Approbation Humaine"
    route-path="/app/cortex-approvals"
    priority="P0"
    gate="Gate 2 Demo-Critical"
    primary-role="SAS d'approbation humaine obligatoire, vue avant/après, pièces justificatives, anti-auto-approbation"
    description="SAS d'approbation obligatoire pour toute action engageante (passage en contrat, remises dérogatoires, règlements de litiges). Présente la vue comparative avant/après, l'accès direct aux pièces justificatives, la révalidation en temps réel et l'idempotence stricte. Les agents IA ne peuvent jamais auto-approuver une demande."
    required-permission="cortex:approvals:decide"
    icon-name="ShieldCheck"
  >
    <!-- Approval Diff Card Preview -->
    <div class="p-4 rounded-xl border border-amber-300 bg-amber-50/50 space-y-3">
      <div class="flex items-center justify-between text-xs">
        <span class="font-bold text-amber-900 uppercase tracking-wider">Demande en Attente #DEMO-APR-001</span>
        <span class="px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-mono font-bold text-[10px]">Supervision Requise</span>
      </div>
      <p class="text-xs text-amber-950 leading-relaxed">
        Dérogation sur le certificat d'assurance pour la production <strong>Trequista Events</strong>. L'agent IA a bloqué la conversion automatique et créé cette demande d'approbation pour décision d'un superviseur.
      </p>
      <div class="flex items-center justify-end gap-2 pt-2 border-t border-amber-200">
        <button class="px-3 py-1.5 rounded-lg border border-red-300 bg-white text-red-700 text-xs font-semibold hover:bg-red-50">
          Rejeter avec motif
        </button>
        <button class="px-3 py-1.5 rounded-lg bg-cortex-primary-600 text-white text-xs font-semibold hover:bg-cortex-primary-700 shadow-xs">
          Approuver et Exécuter
        </button>
      </div>
    </div>
  </ScreenPlaceholderCard>
</template>

<script setup lang="ts">
import ScreenPlaceholderCard from '@/features/common/components/ScreenPlaceholderCard.vue'
</script>
