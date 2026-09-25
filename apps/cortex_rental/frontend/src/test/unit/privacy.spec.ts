import { describe, it, expect } from 'vitest'
import { containsRenterPii, sanitizeOwnerStatement } from '@/utils/privacy'

describe('Privacy Utility Unit Tests', () => {
  it('detects forbidden keys in deeply nested objects', () => {
    const dirty = {
      level1: {
        level2: {
          customer_email: 'leak@demo.local'
        }
      }
    }
    const check = containsRenterPii(dirty)
    expect(check.hasPii).toBe(true)
    expect(check.violations[0]).toContain('level1.level2.customer_email')
  })

  it('detects forbidden keys in arrays of objects', () => {
    const dirty = {
      lines: [
        { id: 1, serial_number: 'SN-001' },
        { id: 2, renter_phone: '514-555-0100' }
      ]
    }
    const check = containsRenterPii(dirty)
    expect(check.hasPii).toBe(true)
    expect(check.violations[0]).toContain('lines[1].renter_phone')
  })

  it('passes cleanly on pure equipment and consignment objects', () => {
    const clean = {
      owner: { id: 'DEMO-OWN-001', display_name: 'Minerva', code: 'MINERVA' },
      period: { start: '2026-08-01', end: '2026-08-31', timezone: 'America/Toronto' },
      currency: 'CAD',
      totals: { eligible_net_revenue: 1000, owner_amount_due: 700 },
      lines: [
        {
          serial_number: 'DEMO-SN-ALX-001',
          equipment_name: 'ARRI Alexa 35',
          rental_start_date: '2026-08-10',
          rental_end_date: '2026-08-17',
          billable_days: 3,
          rate: 1500,
          discount_amount: 0,
          consignment_percentage: 70,
          owner_amount: 3150,
          invoice_reference: 'INV-001'
        }
      ],
      generated_at: '2026-09-01T00:00:00Z',
      snapshot_version: 'v1.0'
    }
    const check = containsRenterPii(clean)
    expect(check.hasPii).toBe(false)
    expect(check.violations).toHaveLength(0)
  })

  it('sanitizes input and removes all dirty fields', () => {
    const dirty = {
      owner: { id: 'DEMO-OWN-001', display_name: 'Minerva', code: 'MINERVA' },
      customer_id: 'CUST-SECRET',
      customer_name: 'Secret Client',
      period: { start: '2026-08-01', end: '2026-08-31', timezone: 'America/Toronto' },
      currency: 'CAD',
      totals: { eligible_net_revenue: 1000, owner_amount_due: 700 },
      lines: []
    }
    const result = sanitizeOwnerStatement(dirty)
    expect(result.isClean).toBe(false)
    expect(result.removedKeys).toContain('customer_id')
    expect(result.removedKeys).toContain('customer_name')
    expect(containsRenterPii(result.sanitized).hasPii).toBe(false)
  })
})
