<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-cortex-bg px-4 font-sans antialiased">
    <div class="w-full max-w-lg p-8 rounded-2xl border border-red-200 bg-cortex-surface shadow-xl space-y-6 text-center">
      <div class="flex items-center justify-center w-16 h-16 rounded-2xl bg-red-100 text-red-700 mx-auto">
        <ShieldAlert class="w-8 h-8" />
      </div>

      <div class="space-y-2">
        <h1 class="text-xl font-bold text-cortex-text-primary tracking-tight">
          Accès Restreint par Policy
        </h1>
        <p class="text-xs text-cortex-text-secondary leading-relaxed max-w-md mx-auto">
          Votre compte ne dispose pas des permissions requises pour accéder à cette ressource opérationnelle.
        </p>
      </div>

      <div v-if="requiredPermission" class="p-3 rounded-xl bg-cortex-surface-subtle border border-cortex-border text-xs text-left space-y-1">
        <span class="text-[10px] uppercase font-bold text-cortex-text-muted">Permission Manquante :</span>
        <div class="font-mono text-xs text-red-700 font-semibold">{{ requiredPermission }}</div>
      </div>

      <div class="flex items-center justify-center gap-3 pt-2">
        <RouterLink
          to="/app/cortex-operations"
          class="px-4 py-2 rounded-xl bg-cortex-primary-600 text-white font-bold text-xs hover:bg-cortex-primary-700 transition-colors shadow-xs"
        >
          Retour au Cockpit Opérations
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ShieldAlert } from 'lucide-vue-next'

const route = useRoute()
const requiredPermission = computed(() => route.query.required as string | undefined)
</script>
