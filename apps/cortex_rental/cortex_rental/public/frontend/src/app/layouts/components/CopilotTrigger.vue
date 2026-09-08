<template>
  <button
    type="button"
    @click="copilotStore.toggle"
    class="relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all focus:outline-none focus:ring-2 focus:ring-cortex-primary-500 shadow-sm"
    :class="[
      copilotStore.isOpen
        ? 'bg-cortex-primary-100 border-cortex-primary-500 text-cortex-primary-900 shadow-cortex-primary-500/20'
        : copilotStore.hasActiveSuggestions
          ? 'bg-cortex-primary-50 border-cortex-primary-400 text-cortex-primary-800 animate-pulse hover:bg-cortex-primary-100'
          : 'bg-cortex-surface border-cortex-border text-cortex-text-primary hover:bg-cortex-surface-subtle'
    ]"
    :aria-label="t('common.copilot_shortcut')"
    :title="t('common.copilot_shortcut')"
  >
    <Sparkles
      class="w-3.5 h-3.5 flex-shrink-0"
      :class="copilotStore.hasActiveSuggestions ? 'text-cortex-primary-600' : 'text-cortex-text-muted'"
    />
    <span class="hidden sm:inline font-sans">Copilot</span>

    <!-- Shortcut Kbd -->
    <kbd class="hidden md:inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-mono rounded bg-cortex-surface border border-cortex-border text-cortex-text-muted">
      ⌘J
    </kbd>

    <!-- Badge for unapproved drafts / proposals -->
    <span
      v-if="copilotStore.unapprovedDraftCount > 0"
      class="flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-cortex-primary-600 text-white flex-shrink-0"
    >
      {{ copilotStore.unapprovedDraftCount }}
    </span>
  </button>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Sparkles } from 'lucide-vue-next'
import { useCopilotStore } from '@/stores/copilot'

const { t } = useI18n()
const copilotStore = useCopilotStore()
</script>
