import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCopilotStore } from '@/stores/copilot'

describe('Copilot Store — Context & Drawer Management', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('C-TEST-1: Controls Copilot drawer open and close state', () => {
    const copilotStore = useCopilotStore()
    expect(copilotStore.isOpen).toBe(false)

    copilotStore.open()
    expect(copilotStore.isOpen).toBe(true)

    copilotStore.close()
    expect(copilotStore.isOpen).toBe(false)

    copilotStore.toggle()
    expect(copilotStore.isOpen).toBe(true)
  })

  it('C-TEST-2: Synchronizes route and entity context dynamically', () => {
    const copilotStore = useCopilotStore()

    copilotStore.syncRouteContext({
      routeName: 'rental-detail',
      path: '/app/cortex-rental/DEMO-TRX-2026-001',
      screenId: 5,
      entityId: 'DEMO-TRX-2026-001'
    })

    expect(copilotStore.activeContext.screenId).toBe(5)
    expect(copilotStore.activeContext.entityId).toBe('DEMO-TRX-2026-001')
    expect(copilotStore.formattedContextLabel).toBe('rental-detail #DEMO-TRX-2026-001')
  })

  it('C-TEST-3: Sends messages and records assistant responses', async () => {
    const copilotStore = useCopilotStore()
    const initialLength = copilotStore.messages.length

    await copilotStore.sendMessage('Vérifier les disponibilités')
    expect(copilotStore.messages.length).toBeGreaterThan(initialLength)
    expect(copilotStore.messages.some(m => m.content === 'Vérifier les disponibilités')).toBe(true)
  })
})
