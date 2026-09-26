import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getCortexApiClient } from '@/api'
import type { AssistantStatus, ChatBlock, ChatContext, ChatMessage, ChatSessionSummary } from '@/api/contracts/ai'
import { i18n } from '@/app/i18n'

/**
 * Assistant state, wired to cortex_rental.api.v1.chat. Nothing here invents
 * an answer: every assistant message is what the server returned, and when
 * the assistant is not configured the drawer says so.
 */

export interface CopilotContext {
  routeName: string
  path: string
  screenId: number
  entityId: string | null
}

/** Route → server page key (AgentRouter.PAGE_TO_AGENT) and the DocType the entity id refers to. */
const ROUTE_PAGES: Record<string, { page: string; doctype?: string }> = {
  'availability-matrix': { page: 'availability' },
  'rental-detail': { page: 'transaction', doctype: 'Cortex Rental Transaction' },
  'rental-composer': { page: 'transaction' },
  'rentals-list': { page: 'transaction' },
  'ai-inbox': { page: 'inbound' },
  'ai-workspace': { page: 'inbound' },
  'checkin-scanner': { page: 'checkin', doctype: 'Cortex Rental Transaction' },
  'consignment-dashboard': { page: 'consignment' },
  'consignment-owners': { page: 'consignment' },
  'owner-statement': { page: 'consignment' }
}

export function chatPageFor(routeName: string): { page: string; doctype?: string } {
  return ROUTE_PAGES[routeName] ?? { page: 'dashboard' }
}

export const useCopilotStore = defineStore('copilot', () => {
  const isOpen = ref(false)
  const status = ref<AssistantStatus | null>(null)
  const statusError = ref('')
  const sessionId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])
  const sessions = ref<ChatSessionSummary[]>([])
  const sending = ref(false)
  const sendError = ref('')

  const activeContext = ref<CopilotContext>({ routeName: 'operations-overview', path: '/operations', screenId: 1, entityId: null })

  const formattedContextLabel = computed(() =>
    activeContext.value.entityId ? `${activeContext.value.routeName} #${activeContext.value.entityId}` : activeContext.value.routeName
  )
  const available = computed(() => status.value?.available === true)

  function toggle() {
    isOpen.value = !isOpen.value
    if (isOpen.value) void loadStatus()
  }
  function open() {
    isOpen.value = true
    void loadStatus()
  }
  function close() {
    isOpen.value = false
  }
  function syncRouteContext(context: CopilotContext) {
    activeContext.value = context
  }

  async function loadStatus(force = false) {
    if (status.value && !force) return
    statusError.value = ''
    try {
      status.value = await getCortexApiClient().getAssistantStatus()
    } catch (error) {
      status.value = null
      statusError.value = error instanceof Error ? error.message : String(error)
    }
  }

  function buildContext(): ChatContext {
    const { page, doctype } = chatPageFor(activeContext.value.routeName)
    const locale = i18n.global.locale.value === 'en-CA' ? 'en-CA' : 'fr-CA'
    const context: ChatContext = { page, locale }
    if (doctype && activeContext.value.entityId) {
      context.active_doctype = doctype
      context.active_document_name = activeContext.value.entityId
    }
    return context
  }

  async function sendMessage(text: string) {
    const message = text.trim()
    if (!message || sending.value) return
    sendError.value = ''
    const now = new Date().toISOString()
    messages.value.push({ id: `local-${Date.now()}`, sender_type: 'Human', text: message, blocks: [], created_at: now })
    sending.value = true
    try {
      const result = await getCortexApiClient().sendChatMessage({ chat_session_id: sessionId.value ?? undefined, message, context: buildContext() })
      sessionId.value = result.chat_session_id
      messages.value.push({ id: result.message_id, sender_type: 'Agent', text: '', blocks: result.blocks, created_at: new Date().toISOString() })
    } catch (error) {
      sendError.value = error instanceof Error ? error.message : String(error)
    } finally {
      sending.value = false
    }
  }

  async function loadSessions() {
    try {
      sessions.value = await getCortexApiClient().listChatSessions()
    } catch {
      sessions.value = []
    }
  }

  async function openSession(name: string) {
    const detail = await getCortexApiClient().getChatSession(name)
    sessionId.value = detail.name
    messages.value = detail.messages
    sendError.value = ''
  }

  function newConversation() {
    sessionId.value = null
    messages.value = []
    sendError.value = ''
  }

  return {
    isOpen,
    status,
    statusError,
    available,
    sessionId,
    messages,
    sessions,
    sending,
    sendError,
    activeContext,
    formattedContextLabel,
    toggle,
    open,
    close,
    syncRouteContext,
    loadStatus,
    buildContext,
    sendMessage,
    loadSessions,
    openSession,
    newConversation
  }
})

export type { ChatBlock }
