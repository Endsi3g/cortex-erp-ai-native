import { describe, it, expect, beforeEach } from 'vitest'
import { MockCortexApiClient } from '@/api/mock/MockCortexApiClient'
import { MockStateStore } from '@/api/mock/MockStateStore'
import { LatencySimulator } from '@/api/mock/LatencySimulator'
import { containsRenterPii, sanitizeOwnerStatement, assertOwnerStatementSafe } from '@/utils/privacy'
import { formatCurrencyCAD as formatCadApp } from '@/app/i18n/formatters'
import { formatCurrencyCAD as formatCadLegacy } from '@/i18n/formatters'
import { formatCurrencyCad as formatCadTypography } from '@/design-system/tokens/typography'
import { initialOwnerStatements } from '@/api/mock/fixtures/consignment'

describe('Gate 1 Challenger Suite — API, State Transitions, Pricing Curve & Privacy Isolation', () => {
  let client: MockCortexApiClient
  let store: MockStateStore

  beforeEach(() => {
    LatencySimulator.setEnabled(false)
    store = new MockStateStore()
    client = new MockCortexApiClient(store)
  })

  // =========================================================================
  // 1. STATE TRANSITIONS & LIFECYCLE STRESS TESTS
  // =========================================================================
  describe('1. MockCortexApiClient State Transitions & Lifecycle Invariants', () => {
    it('1.1 Happy Path progression: Quote -> Reservation -> Contract -> Checked Out -> partial return (stays Checked Out)', async () => {
      // Create quote
      const quoteRes = await client.createQuoteDraft({
        customer_id: 'DEMO-CUST-001',
        starts_at: '2026-10-01T08:00:00Z',
        ends_at: '2026-10-08T08:00:00Z',
        project_name: 'Challenger Workflow Test',
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1 }]
      })
      expect(quoteRes.status).toBe('completed')
      const rentalId = quoteRes.entity_id!
      let rental = await client.getRental({ id: rentalId })
      expect(rental.rental_state).toBe('Quote')

      // Transition to Reservation
      const resRes = await client.requestReservation({ rental_id: rentalId, version: rental.version })
      expect(resRes.status).toBe('completed')
      rental = await client.getRental({ id: rentalId })
      expect(rental.rental_state).toBe('Reservation')

      // Transition to Contract
      const contractRes = await client.requestContractApproval({ rental_id: rentalId, version: rental.version })
      expect(contractRes.status).toBe('completed')
      rental = await client.getRental({ id: rentalId })
      expect(rental.rental_state).toBe('Contract')

      // Start & complete Checkout
      await client.startCheckout({ rental_id: rentalId })
      await client.scanCheckoutSerial({ rental_id: rentalId, serial_number: 'DEMO-SN-ALX-001' })
      const checkoutRes = await client.completeCheckout({ rental_id: rentalId })
      expect(checkoutRes.status).toBe('completed')
      rental = await client.getRental({ id: rentalId })
      expect(rental.rental_state).toBe('Checked Out')

      // Partial Return
      const returnRes = await client.completePartialReturn({ rental_id: rentalId, notes: 'Camera returned' })
      expect(returnRes.status).toBe('completed')
      rental = await client.getRental({ id: rentalId })
      expect(rental.rental_state).toBe('Checked Out')
    })

    it('1.2 VULNERABILITY: Missing transitions for "Returned" (full return) and "Invoiced"', () => {
      // The client interface has no method for completing full return or marking invoiced
      expect((client as unknown as Record<string, unknown>).completeReturn).toBeUndefined()
      expect((client as unknown as Record<string, unknown>).completeCheckin).toBeUndefined()
      expect((client as unknown as Record<string, unknown>).createInvoice).toBeUndefined()
      expect((client as unknown as Record<string, unknown>).finalizeInvoice).toBeUndefined()
    })

    it('1.3 State transition guards prevent illegal state transitions (State Machine Protection)', async () => {
      // DEMO-TRX-2026-003 is initially in Quote state
      const quoteRental = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      expect(quoteRental.rental_state).toBe('Quote')

      // Illegal Transition 1: Checkout directly from Quote without Reservation or Contract is blocked
      const bypassCheckout = await client.completeCheckout({ rental_id: 'DEMO-TRX-2026-003' })
      expect(bypassCheckout.status).toBe('policy_denied')
      const stillQuote = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      expect(stillQuote.rental_state).toBe('Quote')

      // Transition properly: Quote -> Reservation -> Contract
      await client.requestReservation({ rental_id: 'DEMO-TRX-2026-003', version: quoteRental.version })
      const resRental = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      await client.requestContractApproval({ rental_id: 'DEMO-TRX-2026-003', version: resRental.version })
      await client.completeCheckout({ rental_id: 'DEMO-TRX-2026-003' })
      const checkedOutRental = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      expect(checkedOutRental.rental_state).toBe('Checked Out')

      // Illegal Transition 2: Demoting Checked Out back to Reservation is blocked
      const regressed = await client.requestReservation({ rental_id: 'DEMO-TRX-2026-003', version: checkedOutRental.version })
      expect(regressed.status).toBe('policy_denied')
    })

    it('1.4 Concurrency guard: requestReservation validates version parameter and rejects stale context', async () => {
      const rental = await client.getRental({ id: 'DEMO-TRX-2026-003' })
      // Pass completely invalid / stale version
      const res = await client.requestReservation({ rental_id: rental.id, version: -999 })
      expect(res.status).toBe('stale')
      expect(res.stale_context).toBe(true)
    })

    it('1.5 completeCheckout requires Contract state and progresses correctly', async () => {
      const quoteRes = await client.createQuoteDraft({
        customer_id: 'DEMO-CUST-001',
        starts_at: '2026-10-01T08:00:00Z',
        ends_at: '2026-10-08T08:00:00Z',
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 2 }]
      })
      const id = quoteRes.entity_id!
      // Attempting checkout from quote is blocked
      const blockedChk = await client.completeCheckout({ rental_id: id })
      expect(blockedChk.status).toBe('policy_denied')

      // Advance to Contract
      let rental = await client.getRental({ id })
      await client.requestReservation({ rental_id: id, version: rental.version })
      rental = await client.getRental({ id })
      await client.requestContractApproval({ rental_id: id, version: rental.version })

      // Complete checkout
      const chkRes = await client.completeCheckout({ rental_id: id })
      expect(chkRes.status).toBe('completed')
      const updated = await client.getRental({ id })
      expect(updated.rental_state).toBe('Checked Out')
    })
  })

  // =========================================================================
  // 2. 7-DAY CALENDAR = 3-DAY BILLABLE PRICING CURVE CHALLENGE
  // =========================================================================
  describe('2. 7-Day Calendar = 3-Day Billable Pricing Curve & Date Intervals', () => {
    it('2.1 Baseline: 7 calendar days = 3 billable days', async () => {
      const res = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-08T08:00:00Z'
      })
      expect(res.calendar_days).toBe(7)
      expect(res.billable_days).toBe(3)
      expect(res.subtotal).toBe(3000)
    })

    it('2.2 1 calendar day = 1 billable day', async () => {
      const res = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-02T08:00:00Z'
      })
      expect(res.calendar_days).toBe(1)
      expect(res.billable_days).toBe(1)
      expect(res.subtotal).toBe(1000)
    })

    it('2.3 Remediation: No Pricing Inversion between 6 days and 7 days (Piecewise model)', async () => {
      const sixDaysRes = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-07T08:00:00Z' // 6 calendar days
      })
      const sevenDaysRes = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-08T08:00:00Z' // 7 calendar days
      })

      // Piecewise: 6 days -> (0 * 3) + min(6, 3) = 3 billable days -> Subtotal: $3000
      expect(sixDaysRes.billable_days).toBe(3)
      expect(sixDaysRes.subtotal).toBe(3000)

      // 7 days -> (1 * 3) + min(0, 3) = 3 billable days -> Subtotal: $3000
      expect(sevenDaysRes.billable_days).toBe(3)
      expect(sevenDaysRes.subtotal).toBe(3000)

      // Remediation: No pricing inversion! 6 days costs <= 7 days
      expect(sixDaysRes.subtotal).toBeLessThanOrEqual(sevenDaysRes.subtotal)
    })

    it('2.4 Remediation: 14 days (2 weeks) is billed at 6 days (2x 7d=3d)', async () => {
      const res = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-15T08:00:00Z' // 14 calendar days
      })
      expect(res.calendar_days).toBe(14)
      expect(res.billable_days).toBe(6)
      expect(res.subtotal).toBe(6000)
    })

    it('2.5 Edge Case: 0 calendar days (same start and end timestamp)', async () => {
      const res = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-01T08:00:00Z'
      })
      // Math.max(1, 0) forces 1 calendar day
      expect(res.calendar_days).toBe(1)
      expect(res.billable_days).toBe(1)
    })

    it('2.6 Edge Case: Leap Year across Feb 29 (2028-02-27 to 2028-03-05 = 7 days)', async () => {
      const res = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2028-02-27T08:00:00Z',
        ends_at: '2028-03-05T08:00:00Z'
      })
      expect(res.calendar_days).toBe(7)
      expect(res.billable_days).toBe(3)
      expect(res.pricing_rule_applied).toContain('7 jours = 3 jours')
    })

    it('2.7 VULNERABILITY: Negative date range silently coerces to 1 day instead of throwing error', async () => {
      const res = await client.previewPricing({
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1000 }],
        starts_at: '2026-09-10T08:00:00Z',
        ends_at: '2026-09-01T08:00:00Z' // ends before starts!
      })
      // Math.max(1, -9) = 1
      expect(res.calendar_days).toBe(1)
      expect(res.billable_days).toBe(1)
    })

    it('2.8 Remediation: createQuoteDraft dynamically calculates calendar_days and billable_days', async () => {
      // Creating a 1-day quote
      const res = await client.createQuoteDraft({
        customer_id: 'DEMO-CUST-001',
        starts_at: '2026-09-01T08:00:00Z',
        ends_at: '2026-09-02T08:00:00Z', // 1 day
        items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1 }]
      })
      const rental = await client.getRental({ id: res.entity_id! })
      expect(rental.calendar_days).toBe(1)
      expect(rental.billable_days).toBe(1)
    })
  })

  // =========================================================================
  // 3. ADVERSARIAL PRIVACY & OWNERSTATEMENTSAFE STRESS TESTING
  // =========================================================================
  describe('3. Adversarial Stress Test of OwnerStatementSafe & PII Scrubbing', () => {
    const validStatement = initialOwnerStatements['DEMO-OWN-001_2026-08']!

    it('3.1 Standard PII keys in FORBIDDEN_RENTER_PII_KEYS are caught by containsRenterPii', () => {
      const directLeak = {
        ...validStatement,
        customer_name: 'Production Nord Inc.',
        renter_email: 'producer@nord-film.demo',
        project_name: 'Blockbuster Feature'
      }
      const check = containsRenterPii(directLeak)
      expect(check.hasPii).toBe(true)
      expect(check.violations.some((v) => v.includes('customer_name'))).toBe(true)
      expect(check.violations.some((v) => v.includes('renter_email'))).toBe(true)
      expect(check.violations.some((v) => v.includes('project_name'))).toBe(true)
    })

    it('3.2 Remediation: Expanded PII keys (client_phone, billing_address) ARE detected by containsRenterPii', () => {
      const subtleLeak = {
        ...validStatement,
        client_phone: '514-555-0199',
        billing_address: '1000 Rue de la Gauchetière, Montréal, QC'
      }
      const check = containsRenterPii(subtleLeak)
      expect(check.hasPii).toBe(true)
      expect(check.violations.some((v) => v.includes('client_phone'))).toBe(true)
      expect(check.violations.some((v) => v.includes('billing_address'))).toBe(true)
    })

    it('3.3 Remediation: OwnerStatementSafeSchema has .strict(), so assertOwnerStatementSafe throws on unlisted PII', () => {
      const payloadWithUnlistedPii = {
        ...validStatement,
        client_phone: '514-555-0199',
        billing_address: '1000 Rue de la Gauchetière, Montréal, QC'
      }

      // Because containsRenterPii catches them AND OwnerStatementSafeSchema has .strict(),
      // assertOwnerStatementSafe throws!
      expect(() => assertOwnerStatementSafe(payloadWithUnlistedPii)).toThrow()
    })

    it('3.4 Sanitizer behavior: sanitizeOwnerStatement whitelist strips extra keys and reports isClean=false for detected keys', () => {
      const dirtyPayload = {
        ...validStatement,
        client_phone: '514-555-0199',
        billing_address: '1000 Rue de la Gauchetière, Montréal, QC'
      }

      const { sanitized, removedKeys, isClean } = sanitizeOwnerStatement(dirtyPayload)

      // The sanitized output object dropped client_phone and billing_address due to explicit field picking
      expect((sanitized as unknown as Record<string, unknown>).client_phone).toBeUndefined()
      expect((sanitized as unknown as Record<string, unknown>).billing_address).toBeUndefined()

      // removedKeys records them because they are in FORBIDDEN_RENTER_PII_KEYS
      expect(removedKeys.length).toBeGreaterThan(0)
      expect(isClean).toBe(false)
    })

    it('3.5 Nested PII Injection: deep nesting in lines array is stripped by sanitizeOwnerStatement', () => {
      const nestedPii = {
        ...validStatement,
        lines: [
          {
            ...validStatement.lines[0],
            customer_name: 'Secret Client',
            renter_email: 'secret@client.com',
            metadata: {
              customer_address: 'Secret Villa'
            }
          }
        ]
      }

      const { sanitized, removedKeys } = sanitizeOwnerStatement(nestedPii)
      expect(removedKeys.some((k) => k.includes('customer_name'))).toBe(true)
      expect(removedKeys.some((k) => k.includes('renter_email'))).toBe(true)

      const line = sanitized.lines[0] as unknown as Record<string, unknown>
      expect(line.customer_name).toBeUndefined()
      expect(line.renter_email).toBeUndefined()
      expect(line.metadata).toBeUndefined()
    })
  })

  // =========================================================================
  // 4. CAD CURRENCY FORMATTING CHALLENGE (fr-CA & en-CA)
  // =========================================================================
  describe('4. CAD Currency Formatter Stress Testing', () => {
    describe('4.1 app/i18n/formatters.ts (Intl-based)', () => {
      it('formats positive values in fr-CA and en-CA', () => {
        expect(formatCadApp(1920, 'fr-CA')).toBe('1\u00A0920,00\u00A0$')
        expect(formatCadApp(1920, 'en-CA')).toBe('$1,920.00')
      })

      it('formats zero values', () => {
        expect(formatCadApp(0, 'fr-CA')).toBe('0,00\u00A0$')
        expect(formatCadApp(0, 'en-CA')).toBe('$0.00')
      })

      it('formats negative values', () => {
        // fr-CA uses non-breaking space
        const frNeg = formatCadApp(-1920.5, 'fr-CA')
        expect(frNeg).toContain('-1\u00A0920,50\u00A0$')

        const enNeg = formatCadApp(-1920.5, 'en-CA')
        expect(enNeg).toBe('-$1,920.50')
      })

      it('formats large values and decimal fractions', () => {
        expect(formatCadApp(1000000.99, 'fr-CA')).toBe('1\u00A0000\u00A0000,99\u00A0$')
        expect(formatCadApp(1000000.99, 'en-CA')).toBe('$1,000,000.99')
      })

      it('handles NaN gracefully', () => {
        expect(formatCadApp(NaN, 'fr-CA')).toBe('0,00\u00A0$')
        expect(formatCadApp(NaN, 'en-CA')).toBe('$0.00')
      })
    })

    describe('4.2 i18n/formatters.ts (Regex-based legacy implementation)', () => {
      it('Remediation: Negative amounts in en-CA produce valid currency syntax "-$1,920.50"', () => {
        const resultEn = formatCadLegacy(-1920.5, 'en-CA')
        expect(resultEn).toBe('-$1,920.50')
      })

      it('Negative amounts in fr-CA', () => {
        const resultFr = formatCadLegacy(-1920.5, 'fr-CA')
        expect(resultFr).toBe('-1\u00A0920,50\u00A0$')
      })

      it('handles zero and large integers', () => {
        expect(formatCadLegacy(0, 'fr-CA')).toBe('0,00\u00A0$')
        expect(formatCadLegacy(0, 'en-CA')).toBe('$0.00')
        expect(formatCadLegacy(1000000, 'fr-CA')).toBe('1\u00A0000\u00A0000,00\u00A0$')
        expect(formatCadLegacy(1000000, 'en-CA')).toBe('$1,000,000.00')
      })

      it('NaN returns consistent formatted zero with non-breaking space', () => {
        expect(formatCadLegacy(NaN, 'fr-CA')).toBe('0,00\u00A0$')
      })
    })

    describe('4.3 typography.ts (Token-level formatter)', () => {
      it('formats correctly in fr-CA and en-CA', () => {
        const fr = formatCadTypography(1920, 'fr-CA')
        expect(fr.replace(/\u202F/g, '\u00A0')).toContain('1\u00A0920,00')
        const en = formatCadTypography(1920, 'en-CA')
        expect(en).toContain('1,920.00')
      })
    })
  })
})
