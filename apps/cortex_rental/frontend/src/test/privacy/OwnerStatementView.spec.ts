import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { i18n } from '@/app/i18n'
import { createAppRouter } from '@/app/router'
import { setCortexApiClient } from '@/api'
import { MockCortexApiClient } from '@/api/mock'
import { LatencySimulator } from '@/api/mock/LatencySimulator'
import { useSessionStore } from '@/stores/session'
import OwnerStatementView from '@/features/consignment/views/OwnerStatementView.vue'

async function mountStatement(client: MockCortexApiClient) {
  setCortexApiClient(client)
  const router = createAppRouter(true)
  await router.push('/consignment/owners/DEMO-OWN-001/statement/2026-08')
  const wrapper = mount(OwnerStatementView, { global: { plugins: [i18n, router] } })
  await flushPromises()
  return wrapper
}

describe('OwnerStatementView privacy guard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    LatencySimulator.setEnabled(false)
    const session = useSessionStore()
    session.currentUser = { id: 'c@x.test', email: 'c@x.test', full_name: 'C', roles: ['Cortex Consignment Manager'], permissions: ['cortex:consignment:finance'] }
    session.isAuthenticated = true
  })

  it('renders a statement that matches the sealed contract', async () => {
    const wrapper = await mountStatement(new MockCortexApiClient())
    expect(wrapper.text()).toContain('Relevé étanche')
    expect(wrapper.findAll('tbody tr').length).toBeGreaterThan(0)
  })

  it('refuses to display a statement carrying renter identity', async () => {
    const client = new MockCortexApiClient()
    const original = client.getOwnerStatement.bind(client)
    vi.spyOn(client, 'getOwnerStatement').mockImplementation(async input => {
      const result = await original(input)
      return { ...result, statement: { ...result.statement, lines: result.statement.lines.map(line => ({ ...line, customer_name: 'Dune 3 Productions' })) } }
    })
    const wrapper = await mountStatement(client)
    expect(wrapper.text()).not.toContain('Dune 3 Productions')
    expect(wrapper.find('[role="alert"]').text()).toContain('Relevé refusé')
  })
})
