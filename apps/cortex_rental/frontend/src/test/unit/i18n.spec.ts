import { describe, it, expect } from 'vitest'
import frCA from '../../../locales/fr-CA.json'
import enCA from '../../../locales/en-CA.json'

function extractKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  let keys: string[] = []
  for (const [k, v] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      keys = keys.concat(extractKeys(v as Record<string, unknown>, fullKey))
    } else {
      keys.push(fullKey)
    }
  }
  return keys
}

describe('i18n Catalogs Completeness & Parity Tests', () => {
  it('ensures fr-CA and en-CA catalogs have 100% key parity', () => {
    const frKeys = extractKeys(frCA).sort()
    const enKeys = extractKeys(enCA).sort()

    expect(frKeys).toEqual(enKeys)
  })

  it('contains translations for all 7 canonical AI states in both languages', () => {
    const aiStates = [
      'verified',
      'extracted',
      'proposed',
      'needs_confirmation',
      'approval_required',
      'approved_executed',
      'blocked_by_policy'
    ]

    aiStates.forEach((state) => {
      expect(frCA.ai_states).toHaveProperty(state)
      expect(enCA.ai_states).toHaveProperty(state)
      expect((frCA.ai_states as Record<string, { label: string }>)[state]?.label).toBeDefined()
      expect((enCA.ai_states as Record<string, { label: string }>)[state]?.label).toBeDefined()
    })
  })

  it('contains the mandatory privacy banner text in both languages', () => {
    expect(frCA.consignment.privacy_banner).toBe('Informations clients exclues pour la confidentialité des locations.')
    expect(enCA.consignment.privacy_banner).toBe('Customer information excluded for rental confidentiality.')
  })
})
