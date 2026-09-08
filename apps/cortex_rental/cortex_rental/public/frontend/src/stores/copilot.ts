import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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
  toolCall?: {
    name: string
    params: Record<string, unknown>
  }
}

export const useCopilotStore = defineStore('copilot', () => {
  const isOpen = ref<boolean>(false)
  const isStreaming = ref<boolean>(false)
  const canonicalState = ref<CopilotCanonicalState>('idle')
  const unapprovedDraftCount = ref<number>(2)

  const activeContext = ref<CopilotContext>({
    routeName: 'operations-overview',
    path: '/app/cortex-operations',
    screenId: 1,
    entityId: null
  })

  const messages = ref<CopilotMessage[]>([
    {
      id: 'msg-init',
      sender: 'assistant',
      content: 'Bonjour ! Je suis le copilote Cortex. Je surveille les conflits de disponibilité et prépare les soumissions.',
      timestamp: new Date().toISOString(),
      state: 'verified'
    }
  ])

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

  const sendMessage = async (text: string) => {
    if (!text.trim()) return

    const userMsgId = `usr-${Date.now()}`
    messages.value.push({
      id: userMsgId,
      sender: 'user',
      content: text,
      timestamp: new Date().toISOString()
    })

    isStreaming.value = true
    canonicalState.value = 'loading'

    // Simulate backend response
    setTimeout(() => {
      isStreaming.value = false
      canonicalState.value = 'proposed'
      messages.value.push({
        id: `ast-${Date.now()}`,
        sender: 'assistant',
        content: `Proposition pour [${activeContext.value.entityId || 'Opérations'}] : Analyse de l'inventaire effectuée. Aucun conflit de disponibilité détecté.`,
        timestamp: new Date().toISOString(),
        state: 'proposed',
        confidenceScore: 0.96,
        evidenceId: 'DEMO-AUD-002'
      })
    }, 450)
  }

  const clearHistory = () => {
    messages.value = []
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
