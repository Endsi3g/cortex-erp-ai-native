<template>
  <!-- ⌘J: the same conversation, beside the current screen (with its context). Hidden on the home page. -->
  <aside
    v-if="copilot.isOpen && route.name !== 'home'"
    class="claude-surface fixed inset-y-0 right-0 z-40 flex w-full max-w-[440px] flex-col border-l border-[var(--cl-border)] shadow-xl"
    :aria-label="t('copilot.title')"
  >
    <header class="flex h-12 shrink-0 items-center justify-between gap-2 px-4">
      <div class="flex min-w-0 items-center gap-2">
        <Asterisk class="size-5 text-[var(--cl-accent)]" :stroke-width="2.25" aria-hidden="true" />
        <h2 class="claude-serif truncate text-[17px] text-[var(--cl-text)]">{{ t('copilot.title') }}</h2>
      </div>
      <div class="flex items-center gap-0.5">
        <button type="button" class="rounded-lg p-1.5 text-[var(--cl-muted)] hover:bg-[var(--cl-bubble)] hover:text-[var(--cl-text)] disabled:opacity-40" :aria-label="t('ai.new_conversation')" :disabled="!copilot.messages.length" @click="copilot.newConversation()">
          <SquarePen class="size-4" :stroke-width="1.75" />
        </button>
        <button type="button" class="rounded-lg p-1.5 text-[var(--cl-muted)] hover:bg-[var(--cl-bubble)] hover:text-[var(--cl-text)]" :aria-label="t('ai.open_full')" @click="openFull">
          <Maximize2 class="size-4" :stroke-width="1.75" />
        </button>
        <button type="button" class="rounded-lg p-1.5 text-[var(--cl-muted)] hover:bg-[var(--cl-bubble)] hover:text-[var(--cl-text)]" :aria-label="t('copilot.close_drawer')" @click="copilot.close()">
          <X class="size-4" :stroke-width="1.75" />
        </button>
      </div>
    </header>

    <div v-if="copilot.status && !copilot.available" class="px-6 py-10 text-center" role="status">
      <p class="claude-serif text-[18px] text-[var(--cl-text)]">{{ t('ai.assistant_unavailable') }}</p>
      <p class="mt-2 text-[13px] text-[var(--cl-muted)]">{{ t('ai.assistant_unavailable_hint') }}</p>
    </div>
    <p v-else-if="copilot.statusError" class="px-6 py-10 text-center text-[13px] text-ink-red-4" role="alert">{{ copilot.statusError }}</p>

    <template v-else>
      <div ref="scroller" class="min-h-0 flex-1 overflow-y-auto px-4 pb-6 pt-2">
        <p v-if="!copilot.messages.length" class="claude-serif px-1 pt-6 text-[17px] leading-7 text-[var(--cl-muted)]">{{ t('ai.drawer_empty', { context: contextLabel }) }}</p>
        <MessageList :messages="copilot.messages" @open="route => router.push(route)" />
        <p v-if="copilot.sending && !streamingVisible" class="mt-4 flex items-center gap-2 text-[13px] text-[var(--cl-muted)]" role="status">
          <Asterisk class="size-4 animate-spin text-[var(--cl-accent)] [animation-duration:2s]" :stroke-width="2.25" aria-hidden="true" />
          {{ t('ai.thinking') }}
        </p>
        <p v-if="copilot.sendError" class="mt-4 rounded-xl border border-outline-red-1 bg-surface-red-1 px-3 py-2 text-[13px] text-ink-red-4" role="alert">{{ copilot.sendError }}</p>
      </div>
      <div class="shrink-0 px-3 pb-3">
        <ChatComposer compact autofocus :placeholder="t('ai.reply_placeholder')" :send-label="t('ai.send')" :busy="copilot.sending" @send="text => copilot.sendMessage(text)">
          <template #context>{{ t('ai.context_hint', { context: contextLabel }) }}</template>
        </ChatComposer>
      </div>
    </template>
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Asterisk, Maximize2, SquarePen, X } from 'lucide-vue-next'
import { useCopilotStore } from '@/stores/copilot'
import ChatComposer from '@/features/assistant/components/ChatComposer.vue'
import MessageList from '@/features/assistant/components/MessageList.vue'

const { t, te } = useI18n()
const route = useRoute()
const router = useRouter()
const copilot = useCopilotStore()
const scroller = ref<HTMLElement | null>(null)

const contextLabel = computed(() => {
  const key = String(route.meta.titleKey || '')
  const page = key && te(key) ? t(key) : copilot.activeContext.routeName
  return copilot.activeContext.entityId ? `${page} · ${copilot.activeContext.entityId}` : page
})
const streamingVisible = computed(() => copilot.messages.some(m => m.streaming && (m.text || m.blocks.length || m.activeTool)))

watch(() => copilot.messages.map(m => `${m.id}:${m.text.length}:${m.blocks.length}`).join('|'), async () => {
  await nextTick()
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight })
})

function openFull() {
  copilot.close()
  void router.push({ name: 'home', query: copilot.sessionId ? { c: copilot.sessionId } : {} })
}
</script>
