import type { CopilotMessage } from '@/api/contracts'
import { getCsrfToken } from '@/utils/csrf'

interface FrappeResponse<T> {
  message?: { data?: T }
}

interface FrappeRuntime {
  call<T>(options: {
    method: string
    type?: 'GET' | 'POST'
    args?: Record<string, string | undefined>
    callback?: (response: FrappeResponse<T>) => void
    error?: (response: unknown) => void
  }): void
}

interface ChatSessionData { name: string }
interface ChatBlock { type?: string; text?: string; safe_message?: string }
interface ChatResponseData {
  message_id: string
  chat_session_id: string
  status: 'completed' | 'processing'
  blocks: ChatBlock[]
}

/** Desk pages have `frappe.call`; the standalone app (/cortex) has no Frappe globals and talks to the same endpoints with fetch. */
async function callFetch<T>(method: string, args: Record<string, string | undefined>): Promise<T> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(args)) if (value !== undefined) params.set(key, value)
  const csrf = getCsrfToken()
  const response = await fetch(`/api/method/${method}`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', ...(csrf ? { 'X-Frappe-CSRF-Token': csrf } : {}) },
    body: params.toString()
  }).catch(() => null)
  if (!response) throw new Error('La passerelle Cortex est indisponible. Réessaie dans un instant.')
  const body = (await response.json().catch(() => null)) as FrappeResponse<T> | null
  if (!response.ok) throw new Error(response.status === 403 ? 'Votre rôle ne donne pas accès à l’assistant.' : 'La passerelle Cortex est indisponible. Réessaie dans un instant.')
  if (!body?.message?.data) throw new Error('La passerelle Cortex a retourné une réponse vide.')
  return body.message.data
}

function callFrappe<T>(method: string, args: Record<string, string | undefined>): Promise<T> {
  const frappe = (window as Window & { frappe?: FrappeRuntime }).frappe
  if (!frappe?.call) return callFetch<T>(method, args)

  return new Promise((resolve, reject) => {
    frappe.call<T>({
      method,
      type: 'POST',
      args,
      callback: response => {
        if (response.message?.data) resolve(response.message.data)
        else reject(new Error('La passerelle Cortex a retourné une réponse vide.'))
      },
      error: () => reject(new Error('La passerelle Cortex est indisponible. Réessaie dans un instant.'))
    })
  })
}

export async function createAiChatSession(page: string, locale: 'fr-CA' | 'en-CA'): Promise<string> {
  const session = await callFrappe<ChatSessionData>('cortex_rental.api.v1.chat.create_session', { page, locale })
  return session.name
}

export async function sendAiChatMessage(
  content: string,
  sessionId: string,
  context: Record<string, unknown>
): Promise<{ userMessage: CopilotMessage; assistantMessage: CopilotMessage }> {
  const response = await callFrappe<ChatResponseData>('cortex_rental.api.v1.chat.send_message', {
    message: content,
    chat_session_id: sessionId,
    context: JSON.stringify(context)
  })
  const assistantText = response.blocks
    .map(block => block.type === 'assistant_text' ? block.text : block.safe_message)
    .filter((value): value is string => Boolean(value))
    .join('\n\n')

  const timestamp = new Date().toISOString()
  return {
    userMessage: {
      id: `user:${response.message_id}`,
      session_id: response.chat_session_id,
      sender: 'user',
      content,
      state: 'completed',
      timestamp
    },
    assistantMessage: {
      id: response.message_id,
      session_id: response.chat_session_id,
      sender: 'assistant',
      content: assistantText || 'Aucune réponse textuelle exploitable n’a été retournée.',
      // Model prose is an unverified suggestion, never a verified ERP fact.
      state: 'proposed',
      timestamp
    }
  }
}
