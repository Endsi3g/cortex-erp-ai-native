<template>
  <div class="flex flex-wrap items-center gap-2 text-xs py-1" data-test="availability-legend">
    <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-cortex-surface border border-dashed border-cortex-border text-cortex-text-muted">
      <span class="w-2 h-2 rounded-full bg-gray-400"></span>
      <span class="font-medium">{{ t('availability.legend_quote') }}</span>
    </div>
    <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-amber-50 border border-amber-300 text-amber-900">
      <span class="w-2 h-2 rounded-full bg-amber-500"></span>
      <span class="font-medium">{{ t('availability.legend_reservation') }}</span>
    </div>
    <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-blue-50 border border-blue-300 text-blue-900">
      <span class="w-2 h-2 rounded-full bg-blue-500"></span>
      <span class="font-medium">{{ t('availability.legend_contract') }}</span>
    </div>
    <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-purple-50 border border-purple-300 text-purple-900">
      <span class="w-2 h-2 rounded-full bg-purple-500"></span>
      <span class="font-medium">{{ t('availability.legend_checked_out') }}</span>
    </div>
    <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-red-50 border-2 border-red-600 text-red-900 font-semibold" data-test="legend-conflict-indicator">
      <span class="w-2 h-2 rounded-full bg-red-600 animate-pulse"></span>
      <span>{{ t('availability.legend_conflict') }}</span>
    </div>
    <div class="flex items-center gap-1.5 px-2 py-1 rounded bg-red-50/50 border border-red-300 text-red-800">
      <span class="w-2 h-2 rounded-full bg-red-400"></span>
      <span class="font-medium">{{ t('availability.legend_quarantine') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>
