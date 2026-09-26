<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <!-- Unavailable: say so, never simulate an answer. -->
    <div v-if="!copilot.available" class="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center" role="status">
      <Sparkles class="size-6 text-ink-gray-4" :stroke-width="1.5" aria-hidden="true" />
      <p class="text-base font-medium text-ink-gray-8">{{ copilot.status ? t('ai.assistant_unavailable') : copilot.statusError ? t('ai.assistant_status_failed') : t('table.loading') }}</p>
      <p v-if="copilot.status" class="max-w-sm text-p-sm text-ink-gray-5">{{ t('ai.assistant_unavailable_hint') }}</p>
      <p v-else-if="copilot.statusError" class="max-w-sm text-p-sm text-ink-red-4">{{ copilot.statusError }}</p>
      <Button v-if="copilot.statusError" size="sm" variant="subtle" @click="copilot.loadStatus(true)">{{ t('ai.retry') }}</Button>
    </div>

    <template v-else>
      <div ref="scroller" class="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
        <p v-if="!copilot.messages.length" class="text-p-sm text-ink-gray-5">{{ t('ai.empty_conversation') }}</p>
        <div v-for="message in copilot.messages" :key="message.id" :class="message.sender_type === 'Human' ? 'flex justify-end' : ''">
          <div v-if="message.sender_type === 'Human'" class="max-w-[85%] whitespace-pre-wrap rounded-lg bg-surface-gray-2 px-3 py-2 text-p-base text-ink-gray-9">{{ message.text }}</div>
          <div v-else class="space-y-1">
            <ChatBlocks v-if="message.blocks.length" :blocks="message.blocks" />
            <p v-if="!message.blocks.length || message.streaming" class="whitespace-pre-wrap text-p-base text-ink-gray-8">{{ message.text }}<span v-if="message.streaming" class="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-ink-gray-4 align-text-bottom" aria-hidden="true" /></p>
            <p v-if="message.activeTool" class="text-xs text-ink-gray-5" role="status">{{ t('ai.running_tool', { tool: message.activeTool }) }}</p>
            <p v-if="message.model_name" class="text-xs text-ink-gray-4">{{ message.model_name }}</p>
          </div>
        </div>
        <p v-if="copilot.sending && !copilot.messages.some(m => m.streaming && (m.text || m.blocks.length))" class="text-p-sm text-ink-gray-5" role="status">{{ t('ai.thinking') }}</p>
        <p v-if="copilot.sendError" class="rounded border border-outline-red-1 bg-surface-red-1 px-3 py-2 text-p-sm text-ink-red-4" role="alert">{{ copilot.sendError }}</p>
      </div>

      <form class="border-t border-outline-gray-1 p-3" @submit.prevent="submit">
        <label :for="inputId" class="sr-only">{{ t('copilot.placeholder') }}</label>
        <textarea
          :id="inputId"
          v-model="draft"
          rows="2"
          class="block w-full resize-none rounded border-0 bg-surface-gray-2 px-2.5 py-1.5 text-base text-ink-gray-8 placeholder-ink-gray-4 focus:ring-2 focus:ring-outline-gray-3"
          :placeholder="t('copilot.placeholder')"
          maxlength="4000"
          @keydown.enter.exact.prevent="submit"
        />
        <div class="mt-2 flex items-center justify-between gap-2">
          <span class="truncate text-xs text-ink-gray-5">{{ t('ai.context_hint', { context: copilot.formattedContextLabel }) }}</span>
          <Button type="submit" size="sm" variant="solid" :loading="copilot.sending" :disabled="!draft.trim()">{{ t('ai.send') }}</Button>
        </div>
      </form>
    </template>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from 'frappe-ui'
import { Sparkles } from 'lucide-vue-next'
import { useCopilotStore } from '@/stores/copilot'
import ChatBlocks from './ChatBlocks.vue'

const { t } = useI18n()
const copilot = useCopilotStore()
const inputId = useId()
const draft = ref('')
const scroller = ref<HTMLElement | null>(null)

async function submit() {
  const text = draft.value
  if (!text.trim()) return
  draft.value = ''
  await copilot.sendMessage(text)
}

watch(() => copilot.messages.length, async () => {
  await nextTick()
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight })
})

onMounted(() => void copilot.loadStatus())
</script>
