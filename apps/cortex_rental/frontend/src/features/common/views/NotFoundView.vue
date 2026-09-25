<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-cortex-bg px-4 font-sans antialiased">
    <div class="w-full max-w-md p-8 rounded-2xl border border-cortex-border bg-cortex-surface shadow-xl space-y-6 text-center">
      <div class="flex items-center justify-center w-16 h-16 rounded-2xl bg-cortex-primary-50 text-cortex-primary-700 mx-auto">
        <FileQuestion class="w-8 h-8" />
      </div>

      <div class="space-y-2">
        <span class="text-xs font-mono font-bold px-2.5 py-1 rounded bg-cortex-surface-subtle text-cortex-text-muted">
          Erreur 404
        </span>
        <h1 class="text-xl font-bold text-cortex-text-primary tracking-tight">
          Page Introuvable
        </h1>
        <p class="text-xs text-cortex-text-secondary leading-relaxed">
          L'écran ou la ressource demandée n'existe pas ou a été déplacée.
        </p>
      </div>

      <div class="flex items-center justify-center gap-3 pt-2">
        <RouterLink
          to="/operations"
          class="px-4 py-2 rounded-xl bg-cortex-primary-600 text-white font-bold text-xs hover:bg-cortex-primary-700 transition-colors shadow-xs"
        >
          Retour au Cockpit Opérations
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { FileQuestion } from 'lucide-vue-next'
</script>
