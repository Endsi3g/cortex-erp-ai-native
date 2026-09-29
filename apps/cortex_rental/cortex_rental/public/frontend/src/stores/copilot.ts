import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { createAiChatSession, sendChatTurn, type ChatBlockData } from '@/features/intelligence/aiChatGateway'

export type CopilotCanonicalState =
  | 'idle'
  | 'loading'
  | 'tool_running'
  | 'verified'
  | 'extracted'
  | 'proposed'
  | 'needs_confirmation'
  | 'approval_required'
  | 'approved_executed'
  | 'completed'
  | 'blocked_by_policy'
  | 'stale'
  | 'failed'
  | 'permission_denied'
  | 'service_unavailable'

export interface CopilotContext {
  routeName: string
  path: string
  screenId: number
  entityId: string | null
}

export interface CopilotMessage {
  id: string
  sender: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  state?: CopilotCanonicalState
  confidenceScore?: number
  evidenceId?: string
  /** Structured reply blocks from the chat gateway (rendered by ChatBlocks.vue). */
  blocks?: ChatBlockData[]
  toolCall?: {
    name: string
    params: Record<string, unknown>
  }
}

export const useCopilotStore = defineStore('copilot', () => {
  const isOpen = ref<boolean>(false)
  const isStreaming = ref<boolean>(false)
  const canonicalState = ref<CopilotCanonicalState>('idle')
  // Drafts waiting for review are counted by the AI Inbox, not here: no invented badge.
  const unapprovedDraftCount = ref<number>(0)
  const chatSessionId = ref<string>('')

  const activeContext = ref<CopilotContext>({
    routeName: 'operations-overview',
    path: '/app/cortex-operations',
    screenId: 1,
    entityId: null
  })

  const messages = ref<CopilotMessage[]>([])

  // Getters
  const hasActiveSuggestions = computed<boolean>(() => {
    return unapprovedDraftCount.value > 0 || ['proposed', 'approval_required', 'needs_confirmation'].includes(canonicalState.value)
  })

  const formattedContextLabel = computed<string>(() => {
    if (activeContext.value.entityId) {
      return `${activeContext.value.routeName} #${activeContext.value.entityId}`
    }
    return activeContext.value.routeName
  })

  // Actions
  const toggle = () => {
    isOpen.value = !isOpen.value
  }

  const open = () => {
    isOpen.value = true
  }

  const close = () => {
    isOpen.value = false
  }

  const syncRouteContext = (context: CopilotContext) => {
    activeContext.value = context
  }

  const setCanonicalState = (state: CopilotCanonicalState) => {
    canonicalState.value = state
  }

  const contextPage = () => (activeContext.value.routeName.startsWith('rental-detail') ? 'transaction' : 'dashboard')

  // Real call to the authenticated chat gateway. The model answers with suggestions; nothing here executes an action.
  const sendMessage = async (text: string) => {
    const content = text.trim()
    if (!content || isStreaming.value) return

    messages.value.push({ id: `usr-${Date.now()}`, sender: 'user', content, timestamp: new Date().toISOString() })
    isStreaming.value = true
    canonicalState.value = 'loading'

    try {
      const locale = (typeof localStorage !== 'undefined' && localStorage.getItem('cortex_locale') === 'en-CA' ? 'en-CA' : 'fr-CA') as 'fr-CA' | 'en-CA'
      if (!chatSessionId.value) chatSessionId.value = await createAiChatSession(contextPage(), locale)
      const reply = await sendChatTurn(content, chatSessionId.value, {
        page: contextPage(),
        locale,
        active_doctype: activeContext.value.entityId ? 'Cortex Rental Transaction' : undefined,
        active_document_name: activeContext.value.entityId ?? undefined
      })
      canonicalState.value = 'proposed'
      chatSessionId.value = reply.sessionId
      messages.value.push({ id: reply.assistant.id, sender: 'assistant', content: '', blocks: reply.assistant.blocks, timestamp: new Date().toISOString(), state: 'proposed' })
    } catch (error) {
      canonicalState.value = 'service_unavailable'
      messages.value.push({
        id: `err-${Date.now()}`,
        sender: 'assistant',
        content: error instanceof Error ? error.message : "L'assistant est temporairement indisponible.",
        timestamp: new Date().toISOString(),
        state: 'service_unavailable'
      })
    } finally {
      isStreaming.value = false
    }
  }

  const clearHistory = () => {
    messages.value = []
    chatSessionId.value = ''
  }

  return {
    isOpen,
    isStreaming,
    canonicalState,
    unapprovedDraftCount,
    activeContext,
    messages,
    hasActiveSuggestions,
    formattedContextLabel,
    toggle,
    open,
    close,
    syncRouteContext,
    setCanonicalState,
    sendMessage,
    clearHistory
  }
})
