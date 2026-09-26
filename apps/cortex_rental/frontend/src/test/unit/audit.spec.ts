import { describe, it, expect } from 'vitest'
import { computeObjectDiff, computeSha256, formatAuditActionTitle } from '@/utils/audit'

describe('Audit Utility Unit Tests', () => {
  it('computes object diff accurately between states', () => {
    const before = { state: 'Draft', discount: 0, notes: 'Initial' }
    const after = { state: 'Quote', discount: 10, notes: 'Initial' }

    const diffs = computeObjectDiff(before, after)
    expect(diffs).toHaveLength(2)
    expect(diffs.find((d) => d.field === 'state')).toEqual({
      field: 'state',
      oldValue: 'Draft',
      newValue: 'Quote'
    })
    expect(diffs.find((d) => d.field === 'discount')).toEqual({
      field: 'discount',
      oldValue: 0,
      newValue: 10
    })
  })

  it('computes sha256 hash for digital evidence', async () => {
    const hash = await computeSha256('Cortex ERP Digital Evidence Payload')
    expect(hash).toBeDefined()
    expect(hash.length).toBe(64)
  })

  it('formats audit action names to human-readable titles in French', () => {
    expect(formatAuditActionTitle('cortex.rental.quote_created')).toBe('Création du devis')
    expect(formatAuditActionTitle('cortex.rental.checkout_completed')).toBe('Sortie d’équipement (Check-out)')
  })
})
