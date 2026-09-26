<template>
  <!-- Non-modal assistant panel (⌘J), 416px, ERPNext side-panel styling. -->
  <aside
    v-if="copilot.isOpen"
    class="fixed inset-y-0 right-0 z-40 flex w-full max-w-[416px] flex-col border-l border-outline-gray-2 bg-surface-white shadow-xl"
    :aria-label="t('copilot.title')"
  >
    <header class="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-outline-gray-1 px-4">
      <div class="flex min-w-0 items-center gap-2">
        <Sparkles class="size-4 text-ink-gray-7" :stroke-width="1.5" aria-hidden="true" />
        <h2 class="truncate text-base font-semibold text-ink-gray-9">{{ t('copilot.title') }}</h2>
        <span v-if="copilot.status?.model_name" class="truncate text-xs text-ink-gray-5">{{ copilot.status.model_name }}</span>
      </div>
      <div class="flex items-center gap-1">
        <Tooltip :text="t('ai.new_conversation')">
          <Button variant="ghost" size="sm" :aria-label="t('ai.new_conversation')" :disabled="!copilot.messages.length" @click="copilot.newConversation()">
            <template #icon><SquarePen class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Tooltip>
        <Tooltip :text="t('ai.open_full')">
          <Button variant="ghost" size="sm" :aria-label="t('ai.open_full')" @click="openFull">
            <template #icon><Maximize2 class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Tooltip>
        <Button variant="ghost" size="sm" :aria-label="t('copilot.close_drawer')" @click="copilot.close()">
          <template #icon><X class="size-4" :stroke-width="1.5" /></template>
        </Button>
      </div>
    </header>
    <ChatPanel />
  </aside>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button, Tooltip } from 'frappe-ui'
import { Maximize2, Sparkles, SquarePen, X } from 'lucide-vue-next'
import { useCopilotStore } from '@/stores/copilot'
import ChatPanel from '@/features/copilot/components/ChatPanel.vue'

const { t } = useI18n()
const router = useRouter()
const copilot = useCopilotStore()

function openFull() {
  copilot.close()
  void router.push({ name: 'assistant-full' })
}
</script>
