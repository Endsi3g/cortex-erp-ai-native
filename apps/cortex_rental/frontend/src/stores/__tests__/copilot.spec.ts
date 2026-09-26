import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { chatPageFor, useCopilotStore } from '@/stores/copilot'
import { setCortexApiClient } from '@/api'
import type { CortexApiClient } from '@/api'

function fakeClient(overrides: Partial<CortexApiClient>): CortexApiClient {
  return {
    getAssistantStatus: vi.fn().mockResolvedValue({ available: true, provider: 'onyx', model_name: 'test-model' }),
    ...overrides
  } as unknown as CortexApiClient
}

describe('Copilot Store — real chat gateway', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('C-TEST-1: controls the drawer open and close state', () => {
    setCortexApiClient(fakeClient({}))
    const copilotStore = useCopilotStore()
    expect(copilotStore.isOpen).toBe(false)
    copilotStore.open()
    expect(copilotStore.isOpen).toBe(true)
    copilotStore.close()
    expect(copilotStore.isOpen).toBe(false)
    copilotStore.toggle()
    expect(copilotStore.isOpen).toBe(true)
  })

  it('C-TEST-2: sends the server page key and the active document, never an agent name', async () => {
    const sendChatMessage = vi.fn().mockResolvedValue({ message_id: 'M1', chat_session_id: 'S1', status: 'completed', blocks: [{ type: 'assistant_text', text: 'ok', source_ids: [] }] })
    setCortexApiClient(fakeClient({ sendChatMessage }))
    const copilotStore = useCopilotStore()
    copilotStore.syncRouteContext({ routeName: 'rental-detail', path: '/rentals/TRX-1', screenId: 5, entityId: 'TRX-1' })
    expect(copilotStore.formattedContextLabel).toBe('rental-detail #TRX-1')

    await copilotStore.sendMessage('Est-ce prêt ?')
    const input = sendChatMessage.mock.calls[0]![0]
    expect(input.context).toMatchObject({ page: 'transaction', active_doctype: 'Cortex Rental Transaction', active_document_name: 'TRX-1' })
    expect(input).not.toHaveProperty('agent')
    expect(copilotStore.sessionId).toBe('S1')
    expect(copilotStore.messages.map(m => m.sender_type)).toEqual(['Human', 'Agent'])

    await copilotStore.sendMessage('Et ensuite ?')
    expect(sendChatMessage.mock.calls[1]![0].chat_session_id).toBe('S1')
  })

  it('C-TEST-3: a failed call shows the error and invents no assistant message', async () => {
    setCortexApiClient(fakeClient({ sendChatMessage: vi.fn().mockRejectedValue(new Error('Onyx indisponible')) }))
    const copilotStore = useCopilotStore()
    await copilotStore.sendMessage('Bonjour')
    expect(copilotStore.sendError).toBe('Onyx indisponible')
    expect(copilotStore.messages.every(m => m.sender_type === 'Human')).toBe(true)
  })

  it('C-TEST-4: unknown screens fall back to the dashboard agent page', () => {
    expect(chatPageFor('finance-pnl')).toEqual({ page: 'dashboard' })
    expect(chatPageFor('checkin-scanner').page).toBe('checkin')
  })
})
