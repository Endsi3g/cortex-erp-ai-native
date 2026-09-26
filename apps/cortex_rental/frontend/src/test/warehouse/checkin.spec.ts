import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { i18n } from '@/app/i18n'
import { createAppRouter } from '@/app/router'
import { setCortexApiClient } from '@/api'
import { MockCortexApiClient } from '@/api/mock'
import { LatencySimulator } from '@/api/mock/LatencySimulator'
import { useSessionStore } from '@/stores/session'
import CheckinScannerView from '@/features/checkin/views/CheckinScannerView.vue'

async function mountFor(rental: string, client: MockCortexApiClient) {
  setCortexApiClient(client)
  const router = createAppRouter(true)
  await router.push(`/checkin/${rental}`)
  const wrapper = mount(CheckinScannerView, { global: { plugins: [i18n, router] } })
  await flushPromises()
  return wrapper
}

describe('CheckinScannerView payload', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    LatencySimulator.setEnabled(false)
    const session = useSessionStore()
    session.currentUser = { id: 'wh@x.test', email: 'wh@x.test', full_name: 'WH', roles: ['System Manager'], permissions: [] }
    session.isAuthenticated = true
  })

  it('sends scanned units as received and, when settling with loss, the others as missing with 0 returned', async () => {
    const client = new MockCortexApiClient()
    const submit = vi.spyOn(client, 'completePartialReturn')
    const wrapper = await mountFor('DEMO-TRX-2026-001', client)

    await wrapper.find('input[type="text"]').setValue('DEMO-SN-ALX-001')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    await wrapper.find('input[value="settle_with_loss"]').setValue(true)
    await wrapper.findAll('button').find(b => b.text() === 'Valider le retour')!.trigger('click')
    await flushPromises()

    const items = submit.mock.calls[0][0].items!
    const bySerial = Object.fromEntries(items.map(item => [item.serial_no, item]))
    expect(bySerial['DEMO-SN-ALX-001']).toMatchObject({ returned_qty: 1, condition: 'Good', disposition: 'Return to Stock' })
    expect(bySerial['DEMO-SN-CKE-101']).toMatchObject({ returned_qty: 0, condition: 'Missing', disposition: 'Missing' })
    expect(submit.mock.calls[0][0].finalize_mode).toBe('settle_with_loss')
  })
})
