<template>
  <div class="flex h-full min-h-0 flex-col bg-surface-white">
    <PageHeader :title="t('routes.assistant_full')">
      <template #actions>
        <Button size="sm" variant="subtle" :disabled="!copilot.messages.length" @click="copilot.newConversation()">
          <template #prefix><SquarePen class="size-4" :stroke-width="1.5" /></template>
          {{ t('ai.new_conversation') }}
        </Button>
      </template>
    </PageHeader>
    <div class="flex min-h-0 flex-1">
      <nav class="hidden w-[260px] shrink-0 overflow-y-auto border-r border-outline-gray-1 py-2 md:block" :aria-label="t('ai.history')">
        <p class="px-4 pb-1 pt-2 text-xs font-medium uppercase text-ink-gray-5">{{ t('ai.history') }}</p>
        <p v-if="!copilot.sessions.length" class="px-4 py-2 text-p-sm text-ink-gray-5">{{ t('ai.no_history') }}</p>
        <button
          v-for="session in copilot.sessions"
          :key="session.name"
          type="button"
          class="block w-full truncate px-4 py-1.5 text-left text-base hover:bg-surface-gray-2"
          :class="session.name === copilot.sessionId ? 'bg-surface-gray-2 text-ink-gray-9' : 'text-ink-gray-7'"
          :aria-current="session.name === copilot.sessionId ? 'true' : undefined"
          @click="copilot.openSession(session.name)"
        >
          {{ session.title || session.name }}
          <span class="block text-xs text-ink-gray-5">{{ session.last_message_at ? formatDateTime(session.last_message_at, locale as LocaleType) : '' }}</span>
        </button>
      </nav>
      <div class="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col">
        <ChatPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from 'frappe-ui'
import { SquarePen } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import { useCopilotStore } from '@/stores/copilot'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import ChatPanel from '../components/ChatPanel.vue'

const { t, locale } = useI18n()
const copilot = useCopilotStore()

onMounted(async () => {
  await copilot.loadStatus()
  if (copilot.available) await copilot.loadSessions()
})
// Refresh the history once a new conversation got its server id.
watch(() => copilot.sessionId, id => { if (id && !copilot.sessions.some(s => s.name === id)) void copilot.loadSessions() })
</script>
