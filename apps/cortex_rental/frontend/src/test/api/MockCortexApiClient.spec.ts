import { describe, it, expect, beforeEach } from 'vitest'
import { MockCortexApiClient } from '@/api/mock/MockCortexApiClient'
import { MockStateStore } from '@/api/mock/MockStateStore'
import { ErrorInjector } from '@/api/mock/ErrorInjector'
import { LatencySimulator } from '@/api/mock/LatencySimulator'

describe('MockCortexApiClient Comprehensive 32-Method Test Suite', () => {
  let client: MockCortexApiClient

  beforeEach(() => {
    LatencySimulator.setEnabled(false)
    const store = new MockStateStore()
    client = new MockCortexApiClient(store)
  })

  // 1. Availability
  it('1. getAvailabilityMatrix returns rows with provenance metadata', async () => {
    const res = await client.getAvailabilityMatrix({
      start_date: '2026-09-01',
      end_date: '2026-09-08'
    })
    expect(res.provenance).toBe('mock')
    expect(res.rows.length).toBeGreaterThan(0)
    expect(res.rows[0]?.item_code).toBeDefined()
  })

  it('2. checkInventoryAvailability correctly reports available stock', async () => {
    const res = await client.checkInventoryAvailability({
      items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1 }],
      starts_at: '2026-09-10T08:00:00Z',
      ends_at: '2026-09-17T18:00:00Z'
    })
    expect(res.provenance).toBe('mock')
    expect(res.all_available).toBe(true)
    expect(res.items[0]?.is_available).toBe(true)
  })

  it('3. getAvailabilityAlternatives suggests catalog equivalents', async () => {
    const res = await client.getAvailabilityAlternatives({
      item_code: 'DEMO-ITM-ALX35',
      starts_at: '2026-09-10T08:00:00Z',
      ends_at: '2026-09-17T18:00:00Z'
    })
    expect(res.alternatives.length).toBeGreaterThan(0)
    expect(res.alternatives[0]?.item_code).toBe('DEMO-ITM-VRP8K')
  })

  // 2. Rentals & Pricing
  it('4. listRentals returns paginated rental items', async () => {
    const res = await client.listRentals({ page: 1, page_size: 10 })
    expect(res.items.length).toBeGreaterThan(0)
    expect(res.total_count).toBeGreaterThan(0)
  })

  it('5. getRental returns single rental transaction', async () => {
    const res = await client.getRental({ id: 'DEMO-TRX-2026-001' })
    expect(res.id).toBe('DEMO-TRX-2026-001')
    expect(res.customer_name).toBe('Production Nord Inc.')
    expect(res.rental_state).toBe('Checked Out')
  })

  it('6. previewPricing strictly applies the 7d = 3d pricing curve rule', async () => {
    const res = await client.previewPricing({
      items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1, daily_rate: 1500 }],
      starts_at: '2026-09-10T08:00:00Z',
      ends_at: '2026-09-17T08:00:00Z' // 7 days
    })
    expect(res.calendar_days).toBe(7)
    expect(res.billable_days).toBe(3)
    expect(res.subtotal).toBe(4500) // 1500 * 3
    expect(res.pricing_rule_applied).toContain('7 jours = 3 jours')
  })

  it('7. createQuoteDraft creates new rental and records audit event', async () => {
    const initialRentalsCount = client.store.rentals.length
    const initialAuditCount = client.store.auditEvents.length

    const res = await client.createQuoteDraft({
      customer_id: 'DEMO-CUST-001',
      starts_at: '2026-09-20T08:00:00Z',
      ends_at: '2026-09-27T18:00:00Z',
      project_name: 'Test Commercial',
      items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1 }]
    })

    expect(res.status).toBe('completed')
    expect(res.mutation_performed).toBe(true)
    expect(res.entity_id).toBeDefined()
    expect(client.store.rentals.length).toBe(initialRentalsCount + 1)
    expect(client.store.auditEvents.length).toBe(initialAuditCount + 1)
  })

  it('8. updateQuoteDraft modifies existing quote and guards against stale version', async () => {
    const res = await client.updateQuoteDraft({
      rental_id: 'DEMO-TRX-2026-003',
      project_name: 'Updated Project Name',
      version: 1
    })
    expect(res.status).toBe('completed')

    // Concurrency / stale guard test
    const staleRes = await client.updateQuoteDraft({
      rental_id: 'DEMO-TRX-2026-003',
      project_name: 'Conflicting Update',
      version: 1 // now stale
    })
    expect(staleRes.status).toBe('stale')
    expect(staleRes.stale_context).toBe(true)
  })

  it('9. requestReservation transitions quote to reservation state', async () => {
    const res = await client.requestReservation({
      rental_id: 'DEMO-TRX-2026-003',
      version: 1
    })
    expect(res.status).toBe('completed')
    const updated = await client.getRental({ id: 'DEMO-TRX-2026-003' })
    expect(updated.rental_state).toBe('Reservation')
  })

  it('10. requestContractApproval handles readiness checks and triggers approval request if requirements missing', async () => {
    // DEMO-TRX-2026-003 has readiness.overall_ready = false
    const res = await client.requestContractApproval({
      rental_id: 'DEMO-TRX-2026-003',
      version: 1
    })
    expect(res.status).toBe('approval_required')
    expect(res.approval_required).toBe(true)
    expect(res.approval_request_id).toBeDefined()
  })

  it('11. getRentalAudit returns audit history for transaction', async () => {
    const res = await client.getRentalAudit({ rental_id: 'DEMO-TRX-2026-001' })
    expect(res.events.length).toBeGreaterThan(0)
    expect(res.events[0]?.action).toBe('cortex.rental.checkout_completed')
  })

  // 3. Warehouse Field Operations
  it('12. startCheckout returns success mutation', async () => {
    const res = await client.startCheckout({ rental_id: 'DEMO-TRX-2026-002' })
    expect(res.status).toBe('completed')
  })

  it('13. scanCheckoutSerial updates scanned items list in state', async () => {
    const res = await client.scanCheckoutSerial({
      rental_id: 'DEMO-TRX-2026-002',
      serial_number: 'DEMO-SN-ALX-002'
    })
    expect(res.status).toBe('completed')
    expect(res.mutation_performed).toBe(true)
  })

  it('14. completeCheckout transitions rental to Checked Out', async () => {
    const res = await client.completeCheckout({ rental_id: 'DEMO-TRX-2026-002' })
    expect(res.status).toBe('completed')
    const updated = await client.getRental({ id: 'DEMO-TRX-2026-002' })
    expect(updated.rental_state).toBe('Checked Out')
  })

  it('15. startCheckin returns success mutation', async () => {
    const res = await client.startCheckin({ rental_id: 'DEMO-TRX-2026-001' })
    expect(res.status).toBe('completed')
  })

  it('16. scanCheckinSerial registers scanned checkin items', async () => {
    const res = await client.scanCheckinSerial({
      rental_id: 'DEMO-TRX-2026-001',
      serial_number: 'DEMO-SN-ALX-001',
      condition: 'Good'
    })
    expect(res.status).toBe('completed')
  })

  it('17. markSerialMissing updates asset status to Missing', async () => {
    const res = await client.markSerialMissing({
      rental_id: 'DEMO-TRX-2026-001',
      serial_number: 'DEMO-SN-DJI-001',
      reason: 'Lost on mountain location'
    })
    expect(res.status).toBe('completed')
    const serial = await client.getSerial({ serial_number: 'DEMO-SN-DJI-001' })
    expect(serial.status).toBe('Missing')
  })

  it('18. addDamageEvidence sets serial to Quarantine/Repair', async () => {
    const res = await client.addDamageEvidence({
      rental_id: 'DEMO-TRX-2026-001',
      serial_number: 'DEMO-SN-ALX-003',
      description: 'Cracked EVF mount',
      photo_upload_id: 'upl-999',
      severity: 'major'
    })
    expect(res.status).toBe('completed')
    const serial = await client.getSerial({ serial_number: 'DEMO-SN-ALX-003' })
    expect(serial.status).toBe('Under Repair')
  })

  it('19. completePartialReturn keeps the rental Checked Out (server semantics)', async () => {
    const res = await client.completePartialReturn({
      rental_id: 'DEMO-TRX-2026-001',
      notes: 'Lenses returned, camera kept for 2 more days'
    })
    expect(res.status).toBe('completed')
    const updated = await client.getRental({ id: 'DEMO-TRX-2026-001' })
    expect(updated.rental_state).toBe('Checked Out')
  })

  it('20. lookupScan identifies serials and items by barcode', async () => {
    const resSerial = await client.lookupScan({ barcode: 'DEMO-SN-ALX-001' })
    expect(resSerial.entity_type).toBe('serial_number')
    expect(resSerial.display_title).toContain('ARRI Alexa 35')

    const resItem = await client.lookupScan({ barcode: 'DEMO-ITM-APU-600' })
    expect(resItem.entity_type).toBe('item')
  })

  // 4. Consignment & Owner Statements
  it('21. listOwners returns third-party owners', async () => {
    const res = await client.listOwners({})
    expect(res.items.length).toBe(2)
    expect(res.items[0]?.owner_code).toBe('MINERVA')
  })

  it('22. getConsignmentDashboard returns financial totals', async () => {
    const res = await client.getConsignmentDashboard({})
    expect(res.current_month_total_payout).toBeGreaterThan(0)
    expect(res.active_owners_count).toBe(2)
  })

  it('23. getOwnerStatement returns sanitized statement', async () => {
    const res = await client.getOwnerStatement({
      owner_id: 'DEMO-OWN-001',
      period: '2026-08'
    })
    expect(res.statement.owner.code).toBe('MINERVA')
    expect(res.statement.totals.owner_amount_due).toBe(3150)
  })

  it('24. requestOwnerStatementExport records audited statement export', async () => {
    const res = await client.requestOwnerStatementExport({
      owner_id: 'DEMO-OWN-001',
      period: '2026-08',
      format: 'pdf'
    })
    expect(res.status).toBe('completed')
  })

  // 5. Approvals
  it('25. listApprovalRequests returns pending approvals', async () => {
    const res = await client.listApprovalRequests({})
    expect(res.items.length).toBeGreaterThan(0)
  })

  it('26. getApprovalRequest returns single approval item', async () => {
    const res = await client.getApprovalRequest({ id: 'DEMO-APR-001' })
    expect(res.id).toBe('DEMO-APR-001')
    expect(res.approval_type).toBe('Contract Confirmation')
  })

  it('27. approveApprovalRequest resolves approval item', async () => {
    const res = await client.approveApprovalRequest({ id: 'DEMO-APR-001' })
    expect(res.status).toBe('completed')
    const updated = await client.getApprovalRequest({ id: 'DEMO-APR-001' })
    expect(updated.status).toBe('approved')
  })

  it('28. rejectApprovalRequest requires reason and marks rejected', async () => {
    const res = await client.rejectApprovalRequest({
      id: 'DEMO-APR-002',
      reason: 'Commercial discount exceeded budget'
    })
    expect(res.status).toBe('completed')
    const updated = await client.getApprovalRequest({ id: 'DEMO-APR-002' })
    expect(updated.status).toBe('rejected')
    expect(updated.rejection_reason).toBe('Commercial discount exceeded budget')
  })

  // 6. Inbound & Telemetry
  it('29. listInboundRequests returns parsed incoming emails/PDFs', async () => {
    const res = await client.listInboundRequests({})
    expect(res.items.length).toBe(2)
    expect(res.items[0]?.sender_name).toContain('Marc-André')
  })

  it('30. getInboundRequest returns extracted fields and confidence scores', async () => {
    const res = await client.getInboundRequest({ id: 'DEMO-INB-001' })
    expect(res.overall_confidence).toBe(0.94)
    expect(res.extracted_fields.customer_name).toBe('Production Nord Inc.')
  })

  it('31. listAiDrafts returns agent proposals', async () => {
    const res = await client.listAiDrafts({})
    expect(res.items.length).toBeGreaterThan(0)
  })

  it('32. getAgentActivity returns telemetry and tool invocations', async () => {
    const res = await client.getAgentActivity({})
    expect(res.runs.length).toBeGreaterThan(0)
    expect(res.runs[0]?.tools_invoked.length).toBeGreaterThan(0)
  })

  // Error Injection Test
  it('ErrorInjector injects simulated policy denial into mutation', async () => {
    ErrorInjector.setForcedError('policy_denied')
    const res = await client.createQuoteDraft({
      customer_id: 'DEMO-CUST-001',
      starts_at: '2026-09-20T08:00:00Z',
      ends_at: '2026-09-27T18:00:00Z',
      items: [{ item_code: 'DEMO-ITM-ALX35', quantity: 1 }]
    })
    expect(res.status).toBe('policy_denied')
    expect(res.policy_result?.policy_name).toBe('Insurance Minimum Requirement')
  })
})
