<template>
  <div class="claude-surface flex h-full min-h-0">
    <HistoryPanel
      v-if="historyOpen"
      class="hidden md:flex"
      :sessions="copilot.sessions"
      :active-id="copilot.sessionId"
      @new="startNew"
      @open="openConversation"
    />

    <div class="relative flex min-h-0 min-w-0 flex-1 flex-col" :class="artifact ? 'hidden lg:flex lg:max-w-[48%]' : ''">
      <!-- Thin header: history toggle and conversation title -->
      <div class="flex h-11 shrink-0 items-center gap-2 px-3">
        <button
          type="button"
          class="hidden rounded-lg p-1.5 text-[var(--cl-muted)] hover:bg-[var(--cl-bubble)] hover:text-[var(--cl-text)] md:block"
          :aria-label="historyOpen ? t('ai.hide_history') : t('ai.show_history')"
          :aria-pressed="historyOpen"
          @click="toggleHistory"
        >
          <PanelLeft class="size-4" :stroke-width="1.75" />
        </button>
        <p v-if="conversationTitle" class="truncate text-[14px] text-[var(--cl-text)]">{{ conversationTitle }}</p>
        <span v-if="copilot.status?.provider === 'mock'" class="rounded bg-[var(--cl-bubble)] px-1.5 py-0.5 text-[11px] text-[var(--cl-muted)]">DEMO</span>
      </div>

      <!-- Not configured: say so, never simulate -->
      <div v-if="copilot.status && !copilot.available" class="mx-auto mt-16 max-w-md px-6 text-center">
        <Asterisk class="mx-auto size-8 text-[var(--cl-accent)]" :stroke-width="2" aria-hidden="true" />
        <h1 class="claude-serif mt-3 text-[24px] text-[var(--cl-text)]">{{ t('ai.assistant_unavailable') }}</h1>
        <p class="mt-2 text-[14px] text-[var(--cl-muted)]">{{ t('ai.assistant_unavailable_hint') }}</p>
        <RouterLink :to="{ name: 'operations-overview' }" class="mt-5 inline-block text-[14px] text-[var(--cl-accent-hover)] underline">{{ t('ai.go_to_operations') }}</RouterLink>
      </div>
      <p v-else-if="copilot.statusError" class="mx-auto mt-16 max-w-md px-6 text-center text-[14px] text-ink-red-4" role="alert">
        {{ t('ai.assistant_status_failed') }} — {{ copilot.statusError }}
      </p>

      <!-- Empty conversation: greeting, composer, suggestions -->
      <div v-else-if="!copilot.messages.length" class="flex flex-1 flex-col items-center justify-center px-4 pb-[12vh]">
        <h1 class="claude-serif flex items-center gap-3 text-center text-[30px] leading-tight text-[var(--cl-text)] sm:text-[38px]">
          <Asterisk class="size-8 shrink-0 text-[var(--cl-accent)] sm:size-9" :stroke-width="2.25" aria-hidden="true" />
          {{ greeting }}
        </h1>
        <div class="mt-8 w-full max-w-[672px]">
          <ChatComposer ref="composer" :placeholder="t('ai.home_placeholder')" :send-label="t('ai.send')" :busy="copilot.sending" autofocus @send="send">
            <template #context>{{ t('ai.company_context', { company: companyName }) }}</template>
          </ChatComposer>
          <div class="mt-4 flex flex-wrap justify-center gap-2">
            <button
              v-for="suggestion in suggestions"
              :key="suggestion.key"
              type="button"
              class="flex items-center gap-1.5 rounded-lg border border-[var(--cl-border)] bg-[var(--cl-bg)] px-3 py-1.5 text-[13px] text-[#3d3d3a] hover:bg-[var(--cl-bubble)]"
              @click="composer?.fill(suggestion.text)"
            >
              <component :is="suggestion.icon" class="size-3.5 text-[var(--cl-muted)]" :stroke-width="1.75" aria-hidden="true" />
              {{ suggestion.label }}
            </button>
          </div>
        </div>
      </div>

      <!-- Conversation -->
      <template v-else>
        <div ref="scroller" class="min-h-0 flex-1 overflow-y-auto">
          <div class="mx-auto w-full max-w-[720px] px-4 pb-10 pt-6">
            <MessageList :messages="copilot.messages" can-preview @open="openArtifact" />
            <p v-if="copilot.sending && !streamingVisible" class="mt-6 flex items-center gap-2 text-[14px] text-[var(--cl-muted)]" role="status">
              <Asterisk class="size-4 animate-spin text-[var(--cl-accent)] [animation-duration:2s]" :stroke-width="2.25" aria-hidden="true" />
              {{ t('ai.thinking') }}
            </p>
            <p v-if="copilot.sendError" class="mt-6 rounded-xl border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-[14px] text-ink-red-4" role="alert">{{ copilot.sendError }}</p>
          </div>
        </div>
        <div class="shrink-0 bg-gradient-to-t from-[var(--cl-bg)] via-[var(--cl-bg)] to-transparent px-4 pb-4 pt-2">
          <div class="mx-auto w-full max-w-[720px]">
            <ChatComposer :placeholder="t('ai.reply_placeholder')" :send-label="t('ai.send')" :busy="copilot.sending" autofocus @send="send">
              <template #context>{{ t('ai.company_context', { company: companyName }) }}</template>
            </ChatComposer>
            <p class="mt-2 text-center text-[11px] text-[var(--cl-faint)]">{{ t('ai.disclaimer') }}</p>
          </div>
        </div>
      </template>
    </div>

    <ArtifactPanel v-if="artifact" class="flex-1" :route="artifact.route" :title="artifact.title" @close="artifact = null" @navigate="route => router.push(route)" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, type Component } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Asterisk, CalendarRange, FilePlus2, PanelLeft, Receipt, Truck } from 'lucide-vue-next'
import { useCopilotStore } from '@/stores/copilot'
import { useSessionStore } from '@/stores/session'
import ChatComposer from '../components/ChatComposer.vue'
import HistoryPanel from '../components/HistoryPanel.vue'
import MessageList from '../components/MessageList.vue'
import ArtifactPanel from '../components/ArtifactPanel.vue'

const HISTORY_KEY = 'cortex_assistant_history_open'
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const copilot = useCopilotStore()
const session = useSessionStore()
const composer = ref<InstanceType<typeof ChatComposer> | null>(null)
const scroller = ref<HTMLElement | null>(null)
const artifact = ref<{ route: string; title: string } | null>(null)

function openArtifact(route: string, title: string) {
  artifact.value = { route, title }
}

function readHistoryPref(): boolean {
  try { return localStorage.getItem(HISTORY_KEY) !== '0' } catch { return true }
}
const historyOpen = ref(readHistoryPref())
function toggleHistory() {
  historyOpen.value = !historyOpen.value
  try { localStorage.setItem(HISTORY_KEY, historyOpen.value ? '1' : '0') } catch { /* private mode */ }
}

const firstName = computed(() => (session.currentUser?.full_name || '').split(' ')[0] || '')
const companyName = computed(() => session.activeCompany?.name || session.activeCompanyId || '')
const greeting = computed(() => {
  const hour = new Date().getHours()
  const key = hour < 5 || hour >= 18 ? 'ai.greeting_evening' : hour < 12 ? 'ai.greeting_morning' : 'ai.greeting_afternoon'
  return firstName.value ? t(key, { name: firstName.value }) : t('ai.greeting_plain')
})
const conversationTitle = computed(() => copilot.sessions.find(s => s.name === copilot.sessionId)?.title || '')
const streamingVisible = computed(() => copilot.messages.some(m => m.streaming && (m.text || m.blocks.length || m.activeTool)))

interface Suggestion { key: string; label: string; text: string; icon: Component }
const suggestions = computed<Suggestion[]>(() => {
  const all: Array<Suggestion & { permission: string }> = [
    { key: 'today', permission: 'cortex:operations:view', icon: Truck, label: t('ai.suggest_today_label'), text: t('ai.suggest_today') },
    { key: 'availability', permission: 'cortex:availability:view', icon: CalendarRange, label: t('ai.suggest_availability_label'), text: t('ai.suggest_availability') },
    { key: 'quote', permission: 'cortex:quote:create', icon: FilePlus2, label: t('ai.suggest_quote_label'), text: t('ai.suggest_quote') },
    { key: 'invoices', permission: 'cortex:finance:view', icon: Receipt, label: t('ai.suggest_invoices_label'), text: t('ai.suggest_invoices') }
  ]
  return all.filter(s => session.hasPermission(s.permission))
})

async function scrollToEnd() {
  await nextTick()
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
}

async function send(text: string) {
  await copilot.sendMessage(text)
  if (copilot.sessionId && route.query.c !== copilot.sessionId) void router.replace({ query: { c: copilot.sessionId } })
  if (copilot.sessionId && !copilot.sessions.some(s => s.name === copilot.sessionId)) void copilot.loadSessions()
}

function startNew() {
  artifact.value = null
  copilot.newConversation()
  void router.replace({ query: {} })
}

async function openConversation(name: string) {
  try {
    await copilot.openSession(name)
    void router.replace({ query: { c: name } })
    void scrollToEnd()
  } catch (error) {
    copilot.sendError = error instanceof Error ? error.message : String(error)
  }
}

watch(() => copilot.messages.map(m => `${m.id}:${m.text.length}:${m.blocks.length}`).join('|'), () => void scrollToEnd())

onMounted(async () => {
  copilot.syncRouteContext({ routeName: 'home', path: '/', screenId: 20, entityId: null })
  await copilot.loadStatus()
  if (!copilot.available) return
  await copilot.loadSessions()
  const requested = typeof route.query.c === 'string' ? route.query.c : null
  if (requested && requested !== copilot.sessionId) await openConversation(requested)
})
</script>
