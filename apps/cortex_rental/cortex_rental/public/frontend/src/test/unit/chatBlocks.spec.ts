import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ChatBlocks from '@/features/copilot/components/ChatBlocks.vue'

const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }] })
const render = (blocks: Array<Record<string, unknown>>) => mount(ChatBlocks, { props: { blocks: blocks as never }, global: { plugins: [router] } })

describe('ChatBlocks', () => {
  it('renders each gateway block type with its state label', () => {
    const wrapper = render([
      { type: 'assistant_text', text: 'Bonjour' },
      { type: 'verified_fact', title: 'Disponibilité', items: ['3 unités libres'], source_ids: [], checked_at: 'now' },
      { type: 'proposal', title: 'Devis', summary: 'Résumé', impact: ['A'], action: 'open_quote_composer', requires_approval: true },
      { type: 'approval_required', approval_request_id: 'X', action_label: 'Remise', requirements: [{ label: 'Assurance', passed: false }] },
      { type: 'risk', severity: 'danger', title: 'Conflit', explanation: 'Deux réservations' },
      { type: 'missing_information', fields: ['Date de fin'], suggested_next_action: 'Demandez la date' },
      { type: 'extracted_data', title: 'Courriel', fields: [{ label: 'Client', value: 'Dune', confidence: 'low' }] }
    ])
    const types = wrapper.findAll('[data-block]').map((n) => n.attributes('data-block'))
    expect(types).toEqual(['assistant_text', 'verified_fact', 'proposal', 'approval_required', 'risk', 'missing_information', 'extracted_data'])
    expect(wrapper.text()).toContain('Vérifié dans Cortex')
    expect(wrapper.text()).toContain('Proposé — non exécuté')
    expect(wrapper.text()).toContain('Approbation requise')
    expect(wrapper.text()).toContain('✗ Assurance')
    expect(wrapper.text()).toContain('Confiance faible')
  })

  it('never renders model text as HTML', () => {
    const wrapper = render([{ type: 'assistant_text', text: '<img src=x onerror=alert(1)><b>gras</b>' }])
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('b').exists()).toBe(false)
    expect(wrapper.text()).toContain('<img src=x')
  })

  it('shows an unknown block type as a visible error and survives malformed fields', () => {
    const wrapper = render([{ type: 'future_block' }, { type: 'verified_fact', title: 42, items: 'oops' }])
    expect(wrapper.text()).toContain('Contenu non reconnu')
    expect(wrapper.text()).toContain('future_block')
    expect(wrapper.find('[data-block="verified_fact"]').exists()).toBe(true)
  })
})
