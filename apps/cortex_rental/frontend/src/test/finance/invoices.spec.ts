import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { i18n } from '@/app/i18n'
import { createAppRouter } from '@/app/router'
import { setCortexApiClient } from '@/api'
import { MockCortexApiClient } from '@/api/mock'
import { LatencySimulator } from '@/api/mock/LatencySimulator'
import { useSessionStore } from '@/stores/session'
import InvoicesView from '@/features/finance/views/InvoicesView.vue'

describe('InvoicesView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    LatencySimulator.setEnabled(false)
    const session = useSessionStore()
    session.currentUser = { id: 'fin@x.test', email: 'fin@x.test', full_name: 'Finance', roles: ['Cortex Finance Manager'], permissions: ['cortex:finance:view'] }
    session.isAuthenticated = true
  })

  it('lists Cortex invoices with status badges and rental links, flagged as demo', async () => {
    const client = new MockCortexApiClient()
    const spy = vi.spyOn(client, 'listInvoices')
    setCortexApiClient(client)
    const router = createAppRouter(true)
    await router.push('/finance/invoices')
    const wrapper = mount(InvoicesView, { global: { plugins: [i18n, router] } })
    await flushPromises()
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ page: 1, page_size: 20 }))
    expect(wrapper.findAll('tbody tr')).toHaveLength(3)
    expect(wrapper.text()).toContain('Payée en partie')
    expect(wrapper.find('a[href="/rentals/DEMO-TRX-2026-001"]').exists()).toBe(true)
    expect(wrapper.find('[role="status"]').text()).toBe('DEMO')
  })
})
