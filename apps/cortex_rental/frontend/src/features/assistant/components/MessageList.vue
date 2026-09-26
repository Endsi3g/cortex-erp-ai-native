<template>
  <div class="space-y-6" aria-live="polite">
    <div v-for="message in messages" :key="message.id">
      <!-- Person: beige bubble on the right -->
      <div v-if="message.sender_type === 'Human'" class="flex justify-end">
        <div class="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-[var(--cl-bubble)] px-4 py-2.5 text-[15px] leading-6 text-[var(--cl-text)]">{{ message.text }}</div>
      </div>

      <!-- Assistant: plain serif prose, widgets and cards inline, in order -->
      <div v-else class="group space-y-3">
        <template v-for="(block, index) in message.blocks" :key="index">
          <MarkdownText v-if="block.type === 'assistant_text'" :text="block.text" />
          <BlockRenderer v-else :block="block" :can-preview="canPreview" @open="(route, title) => $emit('open', route, title)" />
        </template>
        <MarkdownText v-if="message.streaming || !message.blocks.length" :text="message.text" :streaming="message.streaming" />
        <p v-if="message.activeTool" class="flex items-center gap-1.5 text-sm text-[var(--cl-muted)]" role="status">
          <LoaderCircle class="size-3.5 animate-spin" :stroke-width="2" aria-hidden="true" />
          {{ t('ai.running_tool', { tool: toolLabel(message.activeTool) }) }}
        </p>
        <div v-if="!message.streaming && plainText(message)" class="flex items-center gap-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
          <button type="button" class="rounded-md p-1.5 text-[var(--cl-muted)] hover:bg-[var(--cl-bubble)] hover:text-[var(--cl-text)]" :aria-label="t('ai.copy')" @click="copy(message)">
            <Check v-if="copied === message.id" class="size-4" :stroke-width="1.75" />
            <Copy v-else class="size-4" :stroke-width="1.75" />
          </button>
          <span v-if="message.model_name" class="text-xs text-[var(--cl-faint)]">{{ message.model_name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, Copy, LoaderCircle } from 'lucide-vue-next'
import type { ChatMessage } from '@/api/contracts/ai'
import BlockRenderer from './BlockRenderer.vue'
import MarkdownText from './MarkdownText.vue'

defineProps<{ messages: ChatMessage[]; canPreview?: boolean }>()
defineEmits<{ open: [route: string, title: string] }>()
const { t, te } = useI18n()
const copied = ref<string | null>(null)

function toolLabel(tool: string) {
  return te(`ai.tools.${tool}`) ? t(`ai.tools.${tool}`) : tool
}

function plainText(message: ChatMessage): string {
  const parts = message.blocks.filter(b => b.type === 'assistant_text').map(b => (b as { text: string }).text)
  return parts.length ? parts.join('\n\n') : message.text
}

async function copy(message: ChatMessage) {
  try {
    await navigator.clipboard.writeText(plainText(message))
    copied.value = message.id
    setTimeout(() => { if (copied.value === message.id) copied.value = null }, 1500)
  } catch { /* clipboard refused: nothing to do */ }
}
</script>
