import { describe, it, expect } from 'vitest'
import { containsRenterPii, sanitizeOwnerStatement, assertOwnerStatementSafe } from '@/utils/privacy'
import { initialOwnerStatements, initialOwners, initialConsignmentDashboard } from '@/api/mock/fixtures/consignment'
import { OwnerStatementSafeSchema } from '@/api/contracts/consignment'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '@/stores/session'
import { routes } from '@/app/router/routes'

describe('R10 Privacy & OwnerStatementSafe Isolation Tests (8 Mandatory Invariants)', () => {
  // Test 1: Le rendu Owner Statement ne contient aucune clé interdite
  it('Assertion 1: OwnerStatement structure rejects forbidden renter PII keys', () => {
    const validStatement = initialOwnerStatements['DEMO-OWN-001_2026-08']
    expect(validStatement).toBeDefined()
    const check = containsRenterPii(validStatement)
    expect(check.hasPii).toBe(false)
    expect(check.violations).toHaveLength(0)

    // Ensure corrupted input with renter PII is detected
    const corrupted = {
      ...validStatement,
      customer_name: 'Production Nord Inc.',
      customer_id: 'DEMO-CUST-001'
    }
    const corruptedCheck = containsRenterPii(corrupted)
    expect(corruptedCheck.hasPii).toBe(true)
    expect(corruptedCheck.violations.length).toBeGreaterThanOrEqual(2)
  })

  // Test 2: Les fixtures de consignation ne contiennent aucune PII locataire
  it('Assertion 2: All initial consignment fixtures (owners, dashboard, statements) are completely free of renter PII', () => {
    expect(containsRenterPii(initialOwners).hasPii).toBe(false)
    expect(containsRenterPii(initialConsignmentDashboard).hasPii).toBe(false)
    Object.values(initialOwnerStatements).forEach((statement) => {
      expect(containsRenterPii(statement).hasPii).toBe(false)
      expect(() => assertOwnerStatementSafe(statement)).not.toThrow()
    })
  })

  // Test 3: Les tooltips / descriptions ne contiennent aucune PII locataire
  it('Assertion 3: Consignment line items contain equipment metadata but no project notes or customer contacts in tooltips', () => {
    const statement = initialOwnerStatements['DEMO-OWN-001_2026-08']!
    statement.lines.forEach((line) => {
      expect(line).toHaveProperty('serial_number')
      expect(line).toHaveProperty('equipment_name')
      expect(line).toHaveProperty('invoice_reference')
      expect(line).not.toHaveProperty('project_name')
      expect(line).not.toHaveProperty('project_notes')
      expect(line).not.toHaveProperty('customer_email')
    })
  })

  // Test 4: Les exports UI et les données destinées au PDF utilisent OwnerStatementSafe
  it('Assertion 4: Sanitizer transforms raw transactional data into pure OwnerStatementSafe payload for export', () => {
    const rawTransactionWithPii = {
      owner: {
        id: 'DEMO-OWN-001',
        display_name: 'Minerva Equipment Assets Ltd.',
        code: 'MINERVA'
      },
      customer_id: 'DEMO-CUST-001',
      customer_name: 'Production Nord Inc.',
      customer_email: 'leak@nord-film.demo',
      period: {
        start: '2026-08-01',
        end: '2026-08-31',
        timezone: 'America/Toronto'
      },
      currency: 'CAD',
      totals: {
        eligible_net_revenue: 4500,
        owner_amount_due: 3150
      },
      lines: [
        {
          serial_number: 'DEMO-SN-ALX-001',
          equipment_name: 'ARRI Alexa 35 Camera Package',
          rental_start_date: '2026-08-10',
          rental_end_date: '2026-08-17',
          billable_days: 3,
          rate: 1500,
          discount_amount: 0,
          consignment_percentage: 70,
          owner_amount: 3150,
          invoice_reference: 'INV-2026-08-012',
          customer_payment_information: 'VISA-4242'
        }
      ],
      generated_at: '2026-09-01T00:00:00Z',
      snapshot_version: 'v1.0'
    }

    const { sanitized, removedKeys, isClean } = sanitizeOwnerStatement(rawTransactionWithPii)
    expect(isClean).toBe(false)
    expect(removedKeys).toContain('customer_id')
    expect(removedKeys).toContain('customer_name')
    expect(removedKeys).toContain('customer_email')
    expect(removedKeys).toContain('lines[0].customer_payment_information')

    // Verify sanitized structure conforms to Zod contract
    const parsed = OwnerStatementSafeSchema.safeParse(sanitized)
    expect(parsed.success).toBe(true)
    expect(containsRenterPii(sanitized).hasPii).toBe(false)
  })

  // Test 5: Les console logs frontend ne reçoivent pas l’objet transaction complet
  it('Assertion 5: Sanitized object strips nested communication and project blobs', () => {
    const rawPayload = {
      owner: { id: 'DEMO-OWN-001', display_name: 'Minerva', code: 'MINERVA' },
      period: { start: '2026-08-01', end: '2026-08-31', timezone: 'America/Toronto' },
      currency: 'CAD',
      totals: { eligible_net_revenue: 1000, owner_amount_due: 700 },
      lines: [],
      communication_body: 'Private discussion between rental rep and producer Marc-André',
      project_notes: 'VIP Client discount applied'
    }

    const { sanitized, removedKeys } = sanitizeOwnerStatement(rawPayload)
    expect(removedKeys).toContain('communication_body')
    expect(removedKeys).toContain('project_notes')
    expect((sanitized as unknown as Record<string, unknown>).communication_body).toBeUndefined()
    expect((sanitized as unknown as Record<string, unknown>).project_notes).toBeUndefined()
  })

  // Test 6: Les snapshots E2E / VRT Owner Statement ne contiennent aucune donnée client
  it('Assertion 6: JSON serialization of OwnerStatementSafe validates zero PII occurrences in serialized string', () => {
    const statement = initialOwnerStatements['DEMO-OWN-001_2026-08']!
    const jsonStr = JSON.stringify(statement)
    expect(jsonStr).not.toContain('customer_')
    expect(jsonStr).not.toContain('renter_')
    expect(jsonStr).not.toContain('Production Nord')
    expect(jsonStr).not.toContain('production@nord-film')
  })

  // Test 7: Un rôle non-finance ne voit pas montant dû, lignes financières ou export
  it('Assertion 7: Financial permissions contract requires cortex:consignment:finance role for statement access', () => {
    setActivePinia(createPinia())
    const sessionStore = useSessionStore()

    // Test with user lacking finance permissions
    sessionStore.currentUser = {
      id: 'usr-tech-01',
      full_name: 'Tech 1',
      email: 'tech@cortex.demo',
      roles: ['Warehouse Tech', 'Logistics Staff'],
      permissions: ['cortex:operations:view', 'cortex:checkout:perform']
    }
    expect(sessionStore.hasPermission('cortex:consignment:finance')).toBe(false)
    expect(sessionStore.can('cortex:consignment:finance')).toBe(false)

    // Test with user granted finance role/permissions
    sessionStore.currentUser = {
      id: 'usr-fin-01',
      full_name: 'Finance Lead',
      email: 'finance@cortex.demo',
      roles: ['Finance Lead'],
      permissions: ['cortex:consignment:view', 'cortex:consignment:finance']
    }
    expect(sessionStore.hasPermission('cortex:consignment:finance')).toBe(true)
    expect(sessionStore.can('cortex:consignment:finance')).toBe(true)
  })

  // Test 8: Les URLs vers owner statement ne contiennent aucun customer ID
  it('Assertion 8: Canonical route for Owner Statement uses /app/cortex-owner-statement/:owner/:period with no customer param', () => {
    const ownerStatementRoute = routes.find((r) => r.name === 'owner-statement' || r.meta?.screenId === 15)
    expect(ownerStatementRoute).toBeDefined()
    expect(ownerStatementRoute?.path).toBe('/app/cortex-owner-statement/:owner/:period')
    expect(ownerStatementRoute?.path).not.toContain(':customer')
    expect(ownerStatementRoute?.path).not.toContain(':renter')
    expect(ownerStatementRoute?.path).not.toContain(':rental')
    expect(ownerStatementRoute?.path).not.toContain(':client')
  })
})
