import { describe, it, expect, beforeEach } from 'vitest'
import { OwnerStatementSafeSchema, OwnerStatementLineSafeSchema } from '@/api/contracts/consignment'
import { calculateBillableDays, MockCortexApiClient } from '@/api/mock/MockCortexApiClient'
import { MockStateStore } from '@/api/mock/MockStateStore'
import { LatencySimulator } from '@/api/mock/LatencySimulator'
import { containsRenterPii, sanitizeOwnerStatement, assertOwnerStatementSafe } from '@/utils/privacy'
import { FORBIDDEN_RENTER_PII_KEYS } from '@/types/privacy'
import { initialOwnerStatements } from '@/api/mock/fixtures/consignment'

describe('Gate 1 Adversarial Challenge Suite (Iteration 2) — Empirical Verification', () => {
  let client: MockCortexApiClient
  let store: MockStateStore

  beforeEach(() => {
    LatencySimulator.setEnabled(false)
    store = new MockStateStore()
    client = new MockCortexApiClient(store)
  })

  // =========================================================================
  // 1. PRIVACY HARDENING & PII REJECTION IN OWNER STATEMENT SCHEMAS
  // =========================================================================
  describe('1. Adversarial PII Injection & Schema Strictness', () => {
    const validLine = {
      serial_number: 'DEMO-SN-ALX-001',
      equipment_name: 'ARRI Alexa 35 Camera Package',
      rental_start_date: '2026-08-10',
      rental_end_date: '2026-08-17',
      billable_days: 3,
      rate: 1500,
      discount_amount: 0,
      consignment_percentage: 70,
      owner_amount: 3150,
      invoice_reference: 'INV-2026-08-012'
    }

    const validStatement = initialOwnerStatements['DEMO-OWN-001_2026-08']!

    it('1.1 Baseline: Valid line and statement pass schemas without error', () => {
      const lineResult = OwnerStatementLineSafeSchema.safeParse(validLine)
      expect(lineResult.success).toBe(true)

      const statementResult = OwnerStatementSafeSchema.safeParse(validStatement)
      expect(statementResult.success).toBe(true)
      expect(() => assertOwnerStatementSafe(validStatement)).not.toThrow()
    })

    it('1.2 OwnerStatementLineSafeSchema strictly rejects EVERY forbidden PII key injected', () => {
      // Test injection of every known forbidden PII key into OwnerStatementLineSafeSchema
      for (const piiKey of FORBIDDEN_RENTER_PII_KEYS) {
        const injected = {
          ...validLine,
          [piiKey]: 'LEAKED_PII_DATA_VALUE'
        }
        const result = OwnerStatementLineSafeSchema.safeParse(injected)
        expect(result.success, `Expected line schema to reject injected key: ${piiKey}`).toBe(false)
        if (!result.success) {
          expect(result.error.issues.some((i) => i.code === 'unrecognized_keys')).toBe(true)
        }
      }
    })

    it('1.3 OwnerStatementLineSafeSchema rejects arbitrary unrecognized keys via .strict()', () => {
      const arbitraryKeys = [
        'renter_ssn',
        'customer_tax_id',
        'driver_license',
        'gps_coordinates',
        'renter_comments',
        'vip_status',
        'insurance_policy_number'
      ]

      for (const key of arbitraryKeys) {
        const injected = { ...validLine, [key]: 'secret_value' }
        const result = OwnerStatementLineSafeSchema.safeParse(injected)
        expect(result.success, `Expected line schema to reject unrecognized key: ${key}`).toBe(false)
        if (!result.success) {
          expect(result.error.issues[0]?.code).toBe('unrecognized_keys')
        }
      }
    })

    it('1.4 OwnerStatementSafeSchema rejects root-level PII and unrecognized key injections', () => {
      for (const piiKey of FORBIDDEN_RENTER_PII_KEYS) {
        const injected = {
          ...validStatement,
          [piiKey]: 'LEAKED_PII_ROOT'
        }
        const result = OwnerStatementSafeSchema.safeParse(injected)
        expect(result.success, `Expected statement schema to reject root PII: ${piiKey}`).toBe(false)
        if (!result.success) {
          expect(result.error.issues.some((i) => i.code === 'unrecognized_keys')).toBe(true)
        }
        expect(() => assertOwnerStatementSafe(injected)).toThrow()
      }
    })

    it('1.5 OwnerStatementSafeSchema rejects PII injected into nested owner object', () => {
      const piiInOwner = {
        ...validStatement,
        owner: {
          ...validStatement.owner,
          customer_name: 'Production Nord Inc.',
          client_phone: '514-555-0100'
        }
      }
      const result = OwnerStatementSafeSchema.safeParse(piiInOwner)
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues.some((i) => i.path.includes('owner'))).toBe(true)
      }
      expect(() => assertOwnerStatementSafe(piiInOwner)).toThrow()
    })

    it('1.6 OwnerStatementSafeSchema rejects PII injected into nested period object', () => {
      const piiInPeriod = {
        ...validStatement,
        period: {
          ...validStatement.period,
          project_name: 'Summer Shoot'
        }
      }
      const result = OwnerStatementSafeSchema.safeParse(piiInPeriod)
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues.some((i) => i.path.includes('period'))).toBe(true)
      }
      expect(() => assertOwnerStatementSafe(piiInPeriod)).toThrow()
    })

    it('1.7 OwnerStatementSafeSchema rejects PII injected into nested totals object', () => {
      const piiInTotals = {
        ...validStatement,
        totals: {
          ...validStatement.totals,
          customer_deposit: 5000
        }
      }
      const result = OwnerStatementSafeSchema.safeParse(piiInTotals)
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues.some((i) => i.path.includes('totals'))).toBe(true)
      }
      expect(() => assertOwnerStatementSafe(piiInTotals)).toThrow()
    })

    it('1.8 OwnerStatementSafeSchema rejects statement if ANY line in lines contains PII', () => {
      const taintedStatement = {
        ...validStatement,
        lines: [
          validStatement.lines[0]!,
          {
            ...validStatement.lines[1]!,
            customer_email: 'producer@nord-film.demo'
          }
        ]
      }
      const result = OwnerStatementSafeSchema.safeParse(taintedStatement)
      expect(result.success).toBe(false)
      expect(() => assertOwnerStatementSafe(taintedStatement)).toThrow()
    })

    it('1.9 Sanitizer strips multi-level nested PII and returns schema-compliant statement', () => {
      const multiCorrupted = {
        ...validStatement,
        customer_name: 'Top Secret Client',
        client_phone: '514-555-0999',
        billing_address: '1000 Rue Sherbrooke',
        communication_body: 'Confidential call logs',
        project_notes: 'Urgent delivery notes',
        owner: {
          ...validStatement.owner,
          renter_id: 'CUST-009'
        },
        lines: [
          {
            ...validStatement.lines[0]!,
            customer_payment_information: 'AMEX-1001',
            client_name: 'Secret Producer',
            shipping_address: 'Studio 4B'
          }
        ]
      }

      const checkBefore = containsRenterPii(multiCorrupted)
      expect(checkBefore.hasPii).toBe(true)
      expect(checkBefore.violations.length).toBeGreaterThanOrEqual(7)

      const { sanitized, removedKeys, isClean } = sanitizeOwnerStatement(multiCorrupted)
      expect(isClean).toBe(false)
      expect(removedKeys.length).toBeGreaterThanOrEqual(7)

      // Sanitized output must pass schema validation
      const parseResult = OwnerStatementSafeSchema.safeParse(sanitized)
      expect(parseResult.success).toBe(true)

      const checkAfter = containsRenterPii(sanitized)
      expect(checkAfter.hasPii).toBe(false)
      expect(checkAfter.violations).toHaveLength(0)
    })
  })

  // =========================================================================
  // 2. 7J = 3J PRICING CALCULATION & MONOTONICITY VERIFICATION
  // =========================================================================
  describe('2. 7j=3j Pricing Calculation & Monotonicity Verification', () => {
    // 2.1 Specified target test points
    it('2.1 Correct billable days at exact target milestones: 1d, 3d, 6d, 7d, 8d, 14d, 21d', () => {
      expect(calculateBillableDays(1)).toBe(1)
      expect(calculateBillableDays(3)).toBe(3)
      expect(calculateBillableDays(6)).toBe(3) // 6d capped at 3d
      expect(calculateBillableDays(7)).toBe(3) // 7d = 3d (1 week)
      expect(calculateBillableDays(8)).toBe(4) // 1 week + 1 day = 3 + 1 = 4
      expect(calculateBillableDays(14)).toBe(6) // 2 weeks = 2 * 3 = 6
      expect(calculateBillableDays(21)).toBe(9) // 3 weeks = 3 * 3 = 9
    })

    // 2.2 Strict Monotonicity: price never decreases when duration increases
    it('2.2 Full monotonicity verification across days 1 to 365: calculateBillableDays(d+1) >= calculateBillableDays(d)', () => {
      for (let d = 1; d < 365; d++) {
        const current = calculateBillableDays(d)
        const next = calculateBillableDays(d + 1)
        expect(
          next,
          `Monotonicity failed at day ${d} -> ${d + 1}: current=${current}, next=${next}`
        ).toBeGreaterThanOrEqual(current)

        // Delta between consecutive days must be either 0 (capped during remainder days 3..6) or 1
        const delta = next - current
        expect(delta).toBeGreaterThanOrEqual(0)
        expect(delta).toBeLessThanOrEqual(1)
      }
    })

    // 2.3 Rate factor checks: weekly rate factor is strictly 3/7
    it('2.3 Weekly rate factor invariant: at each full week (7k), billable = 3k', () => {
      for (let w = 1; w <= 52; w++) {
        const calendarDays = w * 7
        const billableDays = calculateBillableDays(calendarDays)
        expect(billableDays).toBe(w * 3)
        // Rate ratio
        expect(billableDays / calendarDays).toBeCloseTo(3 / 7, 5)
      }
    })

    // 2.4 Fractional periods stress test
    it('2.4 Fractional days handling: calculateBillableDays monotonicity on fractional steps (0.1 step)', () => {
      let previous = calculateBillableDays(0.1)
      for (let c = 0.2; c <= 30.0; c += 0.1) {
        const current = calculateBillableDays(Number(c.toFixed(1)))
        expect(
          current,
          `Fractional monotonicity failed at calendar=${c}: prev=${previous}, curr=${current}`
        ).toBeGreaterThanOrEqual(previous)
        previous = current
      }
    })

    it('2.5 Sub-day intervals in previewPricing: rounding and non-inversion', async () => {
      // 6 hours (0.25d) -> Math.max(1, Math.round(0.25)) = 1 day
      const sixHours = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-01T14:00:00Z'
      })
      expect(sixHours.calendar_days).toBe(1)
      expect(sixHours.billable_days).toBe(1)
      expect(sixHours.subtotal).toBe(1000)

      // 36 hours (1.5d) -> Math.round(1.5) = 2 days
      const thirtySixHours = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-02T20:00:00Z'
      })
      expect(thirtySixHours.calendar_days).toBe(2)
      expect(thirtySixHours.billable_days).toBe(2)
      expect(thirtySixHours.subtotal).toBe(2000)

      // 6.5 days (156 hours) -> Math.round(6.5) = 7 days -> 3 billable days
      const sixAndHalfDays = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-07T20:00:00Z'
      })
      expect(sixAndHalfDays.calendar_days).toBe(7)
      expect(sixAndHalfDays.billable_days).toBe(3)
      expect(sixAndHalfDays.subtotal).toBe(3000)

      // 7.5 days -> Math.round(7.5) = 8 days -> 4 billable days
      const sevenAndHalfDays = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-08T20:00:00Z'
      })
      expect(sevenAndHalfDays.calendar_days).toBe(8)
      expect(sevenAndHalfDays.billable_days).toBe(4)
      expect(sevenAndHalfDays.subtotal).toBe(4000)

      // Subtotal monotonicity across increasing intervals
      expect(sixHours.subtotal).toBeLessThanOrEqual(thirtySixHours.subtotal)
      expect(thirtySixHours.subtotal).toBeLessThanOrEqual(sixAndHalfDays.subtotal)
      expect(sixAndHalfDays.subtotal).toBeLessThanOrEqual(sevenAndHalfDays.subtotal)
    })

    it('2.6 Boundary cases: zero and negative durations default to minimum 1 day', () => {
      expect(calculateBillableDays(0)).toBe(1)
      expect(calculateBillableDays(-5)).toBe(1)
    })
  })

  // =========================================================================
  // 3. ILLEGAL STATE TRANSITIONS & CONCURRENCY CONFLICTS
  // =========================================================================
  describe('3. Illegal State Transitions & Concurrency Conflict Enforcement', () => {
    // 3.1 Concurrency conflicts: version check
    it('3.1 updateQuoteDraft rejects stale version with CONCURRENCY_ERROR and status: stale', async () => {
      const quote = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      expect(quote.version).toBe(1)

      // Stale update with wrong version
      const staleRes = await client.updateQuoteDraft({
        rental_id: quote.id,
        version: 999, // mismatch
        project_name: 'Stale update attempt'
      })

      expect(staleRes.status).toBe('stale')
      expect(staleRes.stale_context).toBe(true)
      expect(staleRes.mutation_performed).toBe(false)
      expect(staleRes.errors?.[0]?.code).toBe('CONCURRENCY_ERROR')

      // Valid update with current version succeeds and increments version
      const validRes = await client.updateQuoteDraft({
        rental_id: quote.id,
        version: 1,
        project_name: 'Legit update'
      })
      expect(validRes.status).toBe('completed')
      expect(validRes.mutation_performed).toBe(true)

      const updated = await client.getRental({ id: quote.id })
      expect(updated.version).toBe(2)

      // Previous version 1 is now stale
      const oldVersionRes = await client.updateQuoteDraft({
        rental_id: quote.id,
        version: 1,
        project_name: 'Old version retry'
      })
      expect(oldVersionRes.status).toBe('stale')
      expect(oldVersionRes.stale_context).toBe(true)
    })

    it('3.2 requestReservation rejects stale version with CONCURRENCY_ERROR and status: stale', async () => {
      const quote = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      const staleRes = await client.requestReservation({
        rental_id: quote.id,
        version: quote.version + 50
      })
      expect(staleRes.status).toBe('stale')
      expect(staleRes.stale_context).toBe(true)
      expect(staleRes.errors?.[0]?.code).toBe('CONCURRENCY_ERROR')
    })

    it('3.3 requestContractApproval rejects stale version with CONCURRENCY_ERROR and status: stale', async () => {
      const quote = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      const staleRes = await client.requestContractApproval({
        rental_id: quote.id,
        version: 999
      })
      expect(staleRes.status).toBe('stale')
      expect(staleRes.stale_context).toBe(true)
      expect(staleRes.errors?.[0]?.code).toBe('CONCURRENCY_ERROR')
    })

    // 3.2 State machine enforcement: illegal transitions
    it('3.4 Illegal transition: startCheckout is BLOCKED on Quote state', async () => {
      const res = await client.startCheckout({ rental_id: 'DEMO-TRX-2026-003' })
      expect(res.status).toBe('policy_denied')
      expect(res.mutation_performed).toBe(false)
      expect(res.errors?.[0]?.code).toBe('INVALID_TRANSITION')
    })

    it('3.5 Illegal transition: completeCheckout is BLOCKED on Quote state', async () => {
      const res = await client.completeCheckout({ rental_id: 'DEMO-TRX-2026-003' })
      expect(res.status).toBe('policy_denied')
      expect(res.mutation_performed).toBe(false)
      expect(res.errors?.[0]?.code).toBe('INVALID_TRANSITION')
    })

    it('3.6 Illegal transition: startCheckin is BLOCKED on Quote state', async () => {
      const res = await client.startCheckin({ rental_id: 'DEMO-TRX-2026-003' })
      expect(res.status).toBe('policy_denied')
      expect(res.mutation_performed).toBe(false)
      expect(res.errors?.[0]?.code).toBe('INVALID_STATE')
    })

    it('3.7 Illegal transition: completePartialReturn is BLOCKED on Quote state', async () => {
      const res = await client.completePartialReturn({ rental_id: 'DEMO-TRX-2026-003' })
      expect(res.status).toBe('policy_denied')
      expect(res.mutation_performed).toBe(false)
      expect(res.errors?.[0]?.code).toBe('INVALID_STATE')
    })

    it('3.8 Illegal transition: startCheckin and partialReturn are BLOCKED on Reservation state', async () => {
      // Advance DEMO-TRX-2026-003 to Reservation
      const quote = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      await client.requestReservation({ rental_id: quote.id, version: quote.version })
      const resRental = await client.getRental({ id: quote.id })
      expect(resRental.rental_state).toBe('Reservation')

      // Checkin is forbidden
      const checkinRes = await client.startCheckin({ rental_id: quote.id })
      expect(checkinRes.status).toBe('policy_denied')
      expect(checkinRes.errors?.[0]?.code).toBe('INVALID_STATE')

      // Partial return is forbidden
      const partialRes = await client.completePartialReturn({ rental_id: quote.id })
      expect(partialRes.status).toBe('policy_denied')
      expect(partialRes.errors?.[0]?.code).toBe('INVALID_STATE')
    })

    it('3.9 Illegal transition: requestReservation is BLOCKED when already in Checked Out state', async () => {
      // DEMO-TRX-2026-001 is Checked Out
      const checkedOut = await client.getRental({ id: 'DEMO-TRX-2026-001' })
      expect(checkedOut.rental_state).toBe('Checked Out')

      const res = await client.requestReservation({ rental_id: checkedOut.id, version: checkedOut.version })
      expect(res.status).toBe('policy_denied')
      expect(res.mutation_performed).toBe(false)
      expect(res.errors?.[0]?.code).toBe('INVALID_STATE')
    })

    it('3.10 Illegal transition: completeCheckout is BLOCKED when already Checked Out', async () => {
      const checkedOut = await client.getRental({ id: 'DEMO-TRX-2026-001' })
      const res = await client.completeCheckout({ rental_id: checkedOut.id })
      expect(res.status).toBe('policy_denied')
      expect(res.mutation_performed).toBe(false)
      expect(res.errors?.[0]?.code).toBe('INVALID_TRANSITION')
    })

    // 3.3 Non-existent entity error handling
    it('3.11 Non-existent rental handling: throws or returns NOT_FOUND', async () => {
      // getRental throws
      await expect(client.getRental({ id: 'DEMO-TRX-NONEXISTENT' })).rejects.toThrow(/introuvable/)

      // updateQuoteDraft returns failed + NOT_FOUND
      const updRes = await client.updateQuoteDraft({ rental_id: 'NONEXISTENT', version: 1 })
      expect(updRes.status).toBe('failed')
      expect(updRes.errors?.[0]?.code).toBe('NOT_FOUND')

      // requestReservation returns failed + NOT_FOUND
      const resRes = await client.requestReservation({ rental_id: 'NONEXISTENT', version: 1 })
      expect(resRes.status).toBe('failed')
      expect(resRes.errors?.[0]?.code).toBe('NOT_FOUND')

      // requestContractApproval returns failed + NOT_FOUND
      const appRes = await client.requestContractApproval({ rental_id: 'NONEXISTENT', version: 1 })
      expect(appRes.status).toBe('failed')
      expect(appRes.errors?.[0]?.code).toBe('NOT_FOUND')

      // startCheckout returns failed + NOT_FOUND
      const chkRes = await client.startCheckout({ rental_id: 'NONEXISTENT' })
      expect(chkRes.status).toBe('failed')
      expect(chkRes.errors?.[0]?.code).toBe('NOT_FOUND')

      // completeCheckout returns failed + NOT_FOUND
      const chkCompRes = await client.completeCheckout({ rental_id: 'NONEXISTENT' })
      expect(chkCompRes.status).toBe('failed')
      expect(chkCompRes.errors?.[0]?.code).toBe('NOT_FOUND')

      // startCheckin returns failed + NOT_FOUND
      const chkinRes = await client.startCheckin({ rental_id: 'NONEXISTENT' })
      expect(chkinRes.status).toBe('failed')
      expect(chkinRes.errors?.[0]?.code).toBe('NOT_FOUND')

      // completePartialReturn returns failed + NOT_FOUND
      const partRes = await client.completePartialReturn({ rental_id: 'NONEXISTENT' })
      expect(partRes.status).toBe('failed')
      expect(partRes.errors?.[0]?.code).toBe('NOT_FOUND')
    })

    it('3.12 Non-existent consignment statement throws expected error', async () => {
      await expect(
        client.getOwnerStatement({ owner_id: 'DEMO-OWN-NONEXISTENT', period: '2026-08' })
      ).rejects.toThrow(/introuvable/)
    })
  })
})
