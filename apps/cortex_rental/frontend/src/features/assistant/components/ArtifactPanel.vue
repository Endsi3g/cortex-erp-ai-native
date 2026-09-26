<template>
  <!-- Artifact: the real Cortex page, shown beside the conversation (like Claude's artifacts). -->
  <aside class="flex h-full min-w-0 flex-col border-l border-[var(--cl-border)] bg-white" :aria-label="title">
    <header class="flex h-11 shrink-0 items-center gap-2 border-b border-[var(--cl-border)] bg-[var(--cl-bg)] px-3">
      <PanelRight class="size-4 shrink-0 text-[var(--cl-muted)]" :stroke-width="1.75" aria-hidden="true" />
      <p class="min-w-0 flex-1 truncate text-[14px] text-[var(--cl-text)]">{{ title }}</p>
      <button type="button" class="flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] text-[var(--cl-text)] hover:bg-[var(--cl-bubble)]" @click="$emit('navigate', route)">
        <ArrowUpRight class="size-3.5" :stroke-width="1.75" aria-hidden="true" />{{ t('ai.widget.open_page') }}
      </button>
      <button type="button" class="rounded-md p-1.5 text-[var(--cl-muted)] hover:bg-[var(--cl-bubble)] hover:text-[var(--cl-text)]" :aria-label="t('ai.widget.close_artifact')" @click="$emit('close')">
        <X class="size-4" :stroke-width="1.75" />
      </button>
    </header>
    <iframe :key="src" :src="src" :title="title" class="min-h-0 w-full flex-1 border-0 bg-white" />
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUpRight, PanelRight, X } from 'lucide-vue-next'
import { embedUrl } from '../artifacts'

const props = defineProps<{ route: string; title: string }>()
defineEmits<{ close: []; navigate: [route: string] }>()
const { t } = useI18n()
const src = computed(() => embedUrl(props.route))
</script>
