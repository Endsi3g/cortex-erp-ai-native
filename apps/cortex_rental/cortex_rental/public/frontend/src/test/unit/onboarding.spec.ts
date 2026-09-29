import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { setCortexApiClient } from '@/api'
import { MockCortexApiClient } from '@/api/mock/MockCortexApiClient'
import { LatencySimulator } from '@/api/mock/LatencySimulator'
import OnboardingView from '@/features/onboarding/views/OnboardingView.vue'

describe('Company onboarding', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    LatencySimulator.setEnabled(false)
    setCortexApiClient(new MockCortexApiClient())
  })

  it('mock state is labelled as mock and starts at the profile step', async () => {
    const state = await new MockCortexApiClient().getOnboarding()
    expect(state.provenance).toBe('mock')
    expect(state.steps.map((s) => s.key)).toEqual(['profile', 'team', 'catalog', 'policies'])
    expect(state.steps.find((s) => s.current)?.key).toBe('profile')
    expect(state.steps.filter((s) => !s.optional).map((s) => s.key)).toEqual(['profile'])
  })

  it('saving the profile advances progress and the current step', async () => {
    const client = new MockCortexApiClient()
    const result = await client.saveCompanyProfile({ country: 'Canada', default_currency: 'CAD' })
    expect(result.ok).toBe(true)
    expect(result.state?.progress.done).toBe(1)
    expect(result.state?.steps.find((s) => s.current)?.key).toBe('team')
  })

  it('renders the guided steps with an accessible progress bar and no invented completion', async () => {
    const wrapper = mount(OnboardingView)
    await flushPromises()
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Configurer votre entreprise')
    expect(wrapper.find('[role="progressbar"]').exists()).toBe(true)
    expect(wrapper.findAll('.cx-onb__step').length).toBe(5)
    expect(wrapper.find('.cx-onb__step.is-done').exists()).toBe(false)
  })
})
