<template>
  <RouterLink
    to="/operations"
    class="flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors hover:bg-cortex-surface-subtle group focus:outline-none focus:ring-2 focus:ring-cortex-primary-500"
    :title="t('common.actions.back_to_overview')"
    aria-label="Cortex ERP Logo — Retour au Cockpit d'Opérations"
  >
    <!-- Vector "Control Core" SVG Icon -->
    <div class="relative flex items-center justify-center w-8 h-8 rounded-lg bg-cortex-ink-900 shadow-sm border border-cortex-ink-800 flex-shrink-0">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        class="w-5 h-5 text-cortex-primary-400 transform group-hover:scale-105 transition-transform"
      >
        <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" stroke-opacity="0.35" />
        <circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="2" stroke-opacity="0.8" />
        <circle cx="12" cy="12" r="2" fill="currentColor" />
        <path d="M12 3V5M12 19V21M3 12H5M19 12H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
    </div>

    <!-- Logotype -->
    <div v-if="!collapsed" class="flex flex-col">
      <div class="flex items-center gap-1.5">
        <span class="text-base font-bold tracking-tight text-cortex-ink-900 font-sans leading-none">
          CORTEX
        </span>
        <span class="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-cortex-primary-100 text-cortex-primary-700 uppercase tracking-wider">
          OS
        </span>
      </div>
      <span class="text-[10px] text-cortex-text-muted leading-tight truncate">
        AI-Native Rental ERP
      </span>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

withDefaults(
  defineProps<{
    collapsed?: boolean
  }>(),
  {
    collapsed: false
  }
)

const { t } = useI18n()
</script>
