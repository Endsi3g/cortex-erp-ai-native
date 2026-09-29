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

/** First user-facing message of a failed Frappe call (`_server_messages` is a JSON list of JSON strings), as plain text. */
function serverMessage(raw?: string): string {
  if (!raw) return ''
  try {
    const first = JSON.parse(raw)[0]
    const message = typeof first === 'string' ? JSON.parse(first).message : ''
    return typeof message === 'string' ? message.replace(/<[^>]*>/g, '').trim() : ''
  } catch {
    return ''
  }
}

/** Desk pages have `frappe.call`; the standalone app (/cortex) has no Frappe globals and talks to the same endpoints with fetch. */
async function callFetch<T>(method: string, args: Record<string, string | undefined>, verb: 'GET' | 'POST' = 'POST'): Promise<T> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(args)) if (value !== undefined) params.set(key, value)
  const csrf = getCsrfToken()
  const response = await fetch(`/api/method/${method}${verb === 'GET' && params.size ? `?${params}` : ''}`, {
    method: verb,
    credentials: 'same-origin',
    headers: { Accept: 'application/json', ...(verb === 'POST' ? { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' } : {}), ...(csrf ? { 'X-Frappe-CSRF-Token': csrf } : {}) },
    body: verb === 'POST' ? params.toString() : undefined
  }).catch(() => null)
  if (!response) throw new Error('La passerelle Cortex est indisponible. Réessaie dans un instant.')
  const body = (await response.json().catch(() => null)) as (FrappeResponse<T> & { _server_messages?: string }) | null
  if (!response.ok) throw new Error(serverMessage(body?._server_messages) || (response.status === 403 ? 'Votre rôle ne donne pas accès à l’assistant.' : 'La passerelle Cortex est indisponible. Réessaie dans un instant.'))
  if (!body?.message?.data) throw new Error('La passerelle Cortex a retourné une réponse vide.')
  return body.message.data
}

function callFrappe<T>(method: string, args: Record<string, string | undefined>, verb: 'GET' | 'POST' = 'POST'): Promise<T> {
  const frappe = (window as Window & { frappe?: FrappeRuntime }).frappe
  if (!frappe?.call) return callFetch<T>(method, args, verb)

  return new Promise((resolve, reject) => {
    frappe.call<T>({
      method,
      type: verb,
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

// ---- Structured conversation (full assistant screen, copilot drawer) --------------------------------------------

/** One block of a reply, as sent by the chat gateway (schemas/chat_schemas.py); rendered by ChatBlocks.vue. */
export interface ChatBlockData { type: string; [key: string]: unknown }
export interface ChatTurn { id: string; role: 'user' | 'assistant'; text: string; blocks: ChatBlockData[]; created_at: string | null }
export interface ChatSessionRow { name: string; state: string; started_at: string | null; last_message_at: string | null }

export const listChatSessions = () => callFrappe<ChatSessionRow[]>('cortex_rental.api.v1.chat.list_sessions', {}, 'GET')
export const getChatMessages = (name: string) => callFrappe<ChatTurn[]>('cortex_rental.api.v1.chat.get_messages', { name }, 'GET')

/** Sends a message and returns the assistant turn with its blocks (model prose stays an unverified suggestion). */
export async function sendChatTurn(content: string, sessionId: string, context: Record<string, unknown>): Promise<{ sessionId: string; assistant: ChatTurn }> {
  const response = await callFrappe<ChatResponseData>('cortex_rental.api.v1.chat.send_message', { message: content, chat_session_id: sessionId, context: JSON.stringify(context) })
  return {
    sessionId: response.chat_session_id,
    assistant: { id: response.message_id, role: 'assistant', text: '', blocks: response.blocks as ChatBlockData[], created_at: new Date().toISOString() }
  }
}
