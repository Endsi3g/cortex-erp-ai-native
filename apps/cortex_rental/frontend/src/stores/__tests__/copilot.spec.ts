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

describe('Copilot Store — streaming', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('C-TEST-5: shows streamed text and blocks for its own turn, then the final message', async () => {
    const socket = await import('@/app/realtime/socket')
    let handler: ((event: Record<string, unknown>) => void) | null = null
    const spy = vi.spyOn(socket, 'onRealtime').mockImplementation((_event, fn) => {
      handler = fn as (event: Record<string, unknown>) => void
      return () => { handler = null }
    })
    let resolveSend: (value: unknown) => void = () => {}
    const sendChatMessage = vi.fn().mockImplementation(() => new Promise(resolve => { resolveSend = resolve }))
    setCortexApiClient(fakeClient({ sendChatMessage }))
    const store = useCopilotStore()

    const done = store.sendMessage('Dispo Alexa ?')
    const turn = sendChatMessage.mock.calls[0]![0].client_turn_id as string
    handler!({ session: 'S1', turn: 'someone-else', kind: 'text', delta: 'ignoré' })
    handler!({ session: 'S1', turn, kind: 'text', delta: 'Je ' })
    handler!({ session: 'S1', turn, kind: 'text', delta: 'vérifie.' })
    handler!({ session: 'S1', turn, kind: 'tool', tool: 'check_availability', state: 'running' })
    const live = store.messages.find(m => m.streaming)!
    expect(live.text).toBe('Je vérifie.')
    expect(live.activeTool).toBe('check_availability')
    handler!({ session: 'S1', turn, kind: 'block', type: 'page_link', route: '/availability', label: 'Disponibilité' })
    expect(live.blocks).toEqual([{ type: 'page_link', route: '/availability', label: 'Disponibilité' }])

    resolveSend({ message_id: 'M1', chat_session_id: 'S1', status: 'completed', blocks: [{ type: 'assistant_text', text: 'Je vérifie.', source_ids: [] }] })
    await done
    expect(store.messages.some(m => m.streaming)).toBe(false)
    expect(store.messages.at(-1)!.id).toBe('M1')
    expect(handler).toBeNull()
    spy.mockRestore()
  })
})
