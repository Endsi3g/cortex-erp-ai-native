<template>
  <div class="cx-page cx-assistant" data-test="screen-assistant">
    <CortexPageHeader title="Assistant Cortex" subtitle="Posez une question sur vos locations, votre matériel ou vos règles. Les réponses du modèle sont des suggestions : rien n'est exécuté sans votre confirmation.">
      <template #actions><button type="button" class="cx-btn-primary" data-test="new-chat" @click="startNew">Nouvelle conversation</button></template>
    </CortexPageHeader>

    <div class="cx-assistant__body">
      <aside class="cx-assistant__history" aria-label="Historique des conversations">
        <h2 class="cx-assistant__h">Historique</h2>
        <p v-if="historyError" class="cx-caption" role="alert">{{ historyError }}</p>
        <p v-else-if="!sessions.length" class="cx-caption">Aucune conversation pour l'instant.</p>
        <ul v-else class="cx-assistant__sessions">
          <li v-for="row in sessions" :key="row.name">
            <button type="button" :class="{ 'is-active': row.name === sessionId }" :aria-current="row.name === sessionId ? 'true' : undefined" @click="open(row.name)">{{ sessionLabel(row) }}</button>
          </li>
        </ul>
      </aside>

      <section class="cx-assistant__chat" aria-label="Conversation">
        <div ref="log" class="cx-assistant__log" role="log" aria-live="polite" aria-relevant="additions">
          <div v-if="loadingTurns" class="cx-caption">Chargement de la conversation…</div>
          <div v-else-if="!turns.length && !sending" class="cx-assistant__empty">
            <p><strong>Comment puis-je vous aider ?</strong></p>
            <div class="cx-assistant__starters">
              <button v-for="prompt in starters" :key="prompt" type="button" class="cx-btn-soft" @click="send(prompt)">{{ prompt }}</button>
            </div>
          </div>
          <article v-for="turn in turns" :key="turn.id" class="cx-assistant__turn" :class="`is-${turn.role}`">
            <p class="cx-assistant__who">{{ turn.role === 'user' ? 'Vous' : 'Assistant Cortex' }}</p>
            <p v-if="turn.role === 'user'" class="cx-chat-text" style="margin: 0; white-space: pre-wrap">{{ turn.text }}</p>
            <ChatBlocks v-else :blocks="turn.blocks.length ? turn.blocks : fallback(turn.text)" />
          </article>
          <p v-if="sending" class="cx-caption" role="status">L'assistant prépare une réponse…</p>
          <div v-if="error" class="cx-notice cx-notice--error" role="alert"><div>{{ error }} <button type="button" class="cx-btn-soft" @click="retry">Réessayer</button></div></div>
        </div>

        <form class="cx-assistant__composer" @submit.prevent="send(draft)">
          <label class="sr-only" for="assistant-input">Votre message</label>
          <textarea id="assistant-input" v-model="draft" class="cx-field" rows="2" maxlength="4000" placeholder="Écrivez votre question…" :disabled="sending" @keydown.enter.exact.prevent="send(draft)" />
          <button type="submit" class="cx-btn-primary" :disabled="!draft.trim() || sending">Envoyer</button>
        </form>
        <p class="cx-caption">Entrée pour envoyer, Maj+Entrée pour un saut de ligne. Vos conversations sont privées et conservées selon la politique de rétention de l'entreprise.</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { formatDate } from '@/app/i18n/formatters'
import ChatBlocks from '@/features/copilot/components/ChatBlocks.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import { getChatMessages, listChatSessions, sendChatTurn, createAiChatSession, type ChatBlockData, type ChatSessionRow, type ChatTurn } from '@/features/intelligence/aiChatGateway'

const starters = ['Quelles locations doivent revenir cette semaine ?', 'Quel matériel est disponible du lundi au vendredi prochain ?', 'Résume les approbations en attente.']

const sessions = ref<ChatSessionRow[]>([])
const historyError = ref('')
const sessionId = ref('')
const turns = ref<ChatTurn[]>([])
const draft = ref('')
const sending = ref(false)
const loadingTurns = ref(false)
const error = ref('')
const lastPrompt = ref('')
const log = ref<HTMLElement | null>(null)

const locale = () => (typeof localStorage !== 'undefined' && localStorage.getItem('cortex_locale') === 'en-CA' ? 'en-CA' : 'fr-CA') as 'fr-CA' | 'en-CA'
const fallback = (text: string): ChatBlockData[] => [{ type: 'assistant_text', text }]
const sessionLabel = (row: ChatSessionRow) => `Conversation du ${row.last_message_at || row.started_at ? formatDate((row.last_message_at || row.started_at) as string) : 'jour inconnu'}`
const scrollDown = async () => {
  await nextTick()
  log.value?.scrollTo({ top: log.value.scrollHeight, behavior: 'smooth' })
}

async function refreshHistory() {
  try {
    sessions.value = await listChatSessions()
    historyError.value = ''
  } catch (cause) {
    historyError.value = cause instanceof Error ? cause.message : "L'historique est indisponible."
  }
}

function startNew() {
  sessionId.value = ''
  turns.value = []
  error.value = ''
  draft.value = ''
}

async function open(name: string) {
  if (sending.value) return
  sessionId.value = name
  error.value = ''
  loadingTurns.value = true
  try {
    turns.value = await getChatMessages(name)
    await scrollDown()
  } catch (cause) {
    turns.value = []
    error.value = cause instanceof Error ? cause.message : 'La conversation est indisponible.'
  } finally {
    loadingTurns.value = false
  }
}

async function send(text: string) {
  const content = text.trim()
  if (!content || sending.value) return
  lastPrompt.value = content
  error.value = ''
  sending.value = true
  turns.value = [...turns.value, { id: `local-${Date.now()}`, role: 'user', text: content, blocks: [], created_at: new Date().toISOString() }]
  draft.value = ''
  await scrollDown()
  try {
    if (!sessionId.value) sessionId.value = await createAiChatSession('dashboard', locale())
    const reply = await sendChatTurn(content, sessionId.value, { page: 'dashboard', locale: locale() })
    sessionId.value = reply.sessionId
    turns.value = [...turns.value, reply.assistant]
    await refreshHistory()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "L'assistant est temporairement indisponible."
  } finally {
    sending.value = false
    await scrollDown()
  }
}

function retry() {
  // The failed question is already shown: drop it, then send it again.
  turns.value = turns.value.filter((turn, index) => !(index === turns.value.length - 1 && turn.role === 'user' && turn.text === lastPrompt.value))
  void send(lastPrompt.value)
}

onMounted(refreshHistory)
</script>

<style scoped>
.cx-assistant__body { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 16px; padding: 16px 20px 24px; }
.cx-assistant__history { min-width: 0; }
.cx-assistant__h { margin: 0 0 8px; font-size: 13px; font-weight: 600; }
.cx-assistant__sessions { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; max-height: 60vh; overflow: auto; }
.cx-assistant__sessions button { width: 100%; padding: 8px 10px; border: 1px solid transparent; border-radius: 8px; background: transparent; color: inherit; font: inherit; font-size: 13px; text-align: left; cursor: pointer; }
.cx-assistant__sessions button:hover { background: var(--erp-field, #f3f3f3); }
.cx-assistant__sessions button.is-active { border-color: var(--erp-border, #e5e7eb); background: var(--erp-field, #f3f3f3); font-weight: 600; }
.cx-assistant__chat { display: flex; min-width: 0; min-height: 60vh; flex-direction: column; gap: 8px; }
.cx-assistant__log { display: grid; flex: 1; align-content: start; gap: 16px; min-height: 320px; max-height: 62vh; overflow: auto; padding: 4px; }
.cx-assistant__empty { display: grid; gap: 12px; padding: 24px 0; }
.cx-assistant__starters { display: flex; flex-wrap: wrap; gap: 8px; }
.cx-assistant__turn { display: grid; gap: 6px; max-width: 760px; }
.cx-assistant__turn.is-user { justify-self: end; padding: 10px 14px; border-radius: 10px; background: var(--erp-field, #f3f3f3); }
.cx-assistant__who { margin: 0; color: var(--erp-muted, #525252); font-size: 12px; font-weight: 600; }
.cx-assistant__composer { display: flex; align-items: flex-end; gap: 8px; }
.cx-assistant__composer textarea { flex: 1; resize: vertical; padding: 8px 12px; }
@media (max-width: 860px) {
  .cx-assistant__body { grid-template-columns: 1fr; padding: 12px; }
  .cx-assistant__sessions { max-height: 160px; }
  .cx-assistant__log { max-height: none; }
}
</style>
