<template>
  <nav class="flex h-full w-[260px] shrink-0 flex-col border-r border-[var(--cl-border)] bg-[var(--cl-panel)]" :aria-label="t('ai.history')">
    <div class="p-3">
      <button
        type="button"
        class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[14px] font-medium text-[var(--cl-text)] hover:bg-[var(--cl-bubble)]"
        @click="$emit('new')"
      >
        <span class="flex size-6 items-center justify-center rounded-full bg-[var(--cl-accent)] text-white"><Plus class="size-3.5" :stroke-width="2.5" aria-hidden="true" /></span>
        {{ t('ai.new_conversation') }}
      </button>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
      <p v-if="!sessions.length" class="px-2.5 py-2 text-[13px] text-[var(--cl-muted)]">{{ t('ai.no_history') }}</p>
      <template v-for="group in groups" :key="group.key">
        <p class="px-2.5 pb-1 pt-4 text-[12px] font-medium text-[var(--cl-muted)]">{{ t(`ai.history_${group.key}`) }}</p>
        <button
          v-for="session in group.items"
          :key="session.name"
          type="button"
          class="block w-full truncate rounded-lg px-2.5 py-1.5 text-left text-[14px] hover:bg-[var(--cl-bubble)]"
          :class="session.name === activeId ? 'bg-[var(--cl-bubble)] text-[var(--cl-text)]' : 'text-[#3d3d3a]'"
          :aria-current="session.name === activeId ? 'true' : undefined"
          @click="$emit('open', session.name)"
        >
          {{ session.title || t('ai.untitled') }}
        </button>
      </template>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus } from 'lucide-vue-next'
import type { ChatSessionSummary } from '@/api/contracts/ai'
import { parseFrappeDate } from '@/app/i18n/formatters'

const props = defineProps<{ sessions: ChatSessionSummary[]; activeId: string | null }>()
defineEmits<{ new: []; open: [name: string] }>()
const { t } = useI18n()

const groups = computed(() => {
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const buckets: Record<'today' | 'week' | 'older', ChatSessionSummary[]> = { today: [], week: [], older: [] }
  for (const session of props.sessions) {
    const stamp = session.last_message_at || session.started_at
    const time = stamp ? parseFrappeDate(stamp).getTime() : 0
    if (time >= startOfToday) buckets.today.push(session)
    else if (time >= startOfToday - 6 * 86400000) buckets.week.push(session)
    else buckets.older.push(session)
  }
  return (['today', 'week', 'older'] as const).filter(key => buckets[key].length).map(key => ({ key, items: buckets[key] }))
})
</script>
