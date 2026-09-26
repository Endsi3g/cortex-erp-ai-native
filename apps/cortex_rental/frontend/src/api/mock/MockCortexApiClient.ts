import type { CortexApiClient } from '../CortexApiClient'
import type {
  AvailabilityMatrixInput,
  AvailabilityMatrixResponse,
  AvailabilityCheckInput,
  AvailabilityCheckResponse,
  AlternativesInput,
  AlternativesResponse,
  ListRentalsInput,
  ListRentalsResponse,
  GetRentalInput,
  GetRentalResponse,
  RentalCustomerOption,
  RentalCatalogOption,
  PreviewPricingInput,
  PreviewPricingResponse,
  CreateQuoteDraftInput,
  UpdateQuoteDraftInput,
  RequestReservationInput,
  RequestContractApprovalInput,
  GetRentalAuditInput,
  GetRentalAuditResponse,
  StartCheckoutInput,
  ScanCheckoutSerialInput,
  CompleteCheckoutInput,
  StartCheckinInput,
  ScanCheckinSerialInput,
  MarkSerialMissingInput,
  AddDamageEvidenceInput,
  CompletePartialReturnInput,
  LookupScanInput,
  LookupScanResponse,
  ListOwnersInput,
  ListOwnersResponse,
  ConsignmentDashboardInput,
  ConsignmentDashboardResponse,
  OwnerStatementInput,
  OwnerStatementResponse,
  ConsignmentOwnerRecord,
  OwnerDraft,
  CustomerRecord,
  ListCustomersInput,
  ListCustomersResponse,
  NewCustomerInput,
  ListApprovalRequestsInput,
  ListApprovalsResponse,
  GetApprovalRequestInput,
  GetApprovalResponse,
  ApproveApprovalInput,
  RejectApprovalInput,
  ListEquipmentInput,
  ListEquipmentResponse,
  GetEquipmentInput,
  GetEquipmentResponse,
  GetSerialInput,
  GetSerialResponse,
  ListKitsInput,
  ListKitsResponse,
  EquipmentProfileChanges,
  SerialStatus,
  RentalKit,
  ListRentalPoliciesInput,
  ListRentalPoliciesResponse,
  GetTeamRolesInput,
  TeamRolesResponse,
  ListMigrationBatchesInput,
  MigrationBatchesResponse,
  ListAuditEventsInput,
  ListAuditEventsResponse,
  CreateUploadIntentInput,
  UploadIntentResponse,
  RegisterEvidenceInput,
  MutationResponse
} from '../contracts'
import type { InboxKind, InboxList, InboxDetail, AgentActivity, AgentActivityInput, AssistantStatus, ChatSessionSummary, ChatSessionDetail, SendChatInput, SendChatResult } from '../contracts/ai'
import type { PnlFilterOptions, PnlFilters, PnlReport, GlobalSearchResponse } from '../contracts'
import { demoPnlFilterOptions, demoProfitAndLoss } from './fixtures/finance'
import type { RentalSummary, ListRentalSummariesInput, ReadinessField, OperationsOverview } from '../contracts'
import type { ConsignmentOwner } from '../contracts'
import type { InvoiceRow, PaymentRow, PagedResult, ListInvoicesInput, ListPaymentsInput, RentalBilling, PaymentMode, RecordAdvanceInput, RecordAdvanceResult } from '../contracts'
import { demoInvoices, demoPayments } from './fixtures/billing'
import { demoActions } from './fixtures/rentals'

import { MockStateStore } from './MockStateStore'
import { LatencySimulator } from './LatencySimulator'
import { ErrorInjector } from './ErrorInjector'
import type { RentalTransaction, RentalLineItem } from '@/types/rental'

export function calculateBillableDays(calendarDays: number): number {
  if (calendarDays <= 0) return 1
  const weeks = Math.floor(calendarDays / 7)
  const remainder = calendarDays % 7
  return (weeks * 3) + Math.min(remainder, 3)
}

export class MockCortexApiClient implements CortexApiClient {
  public store: MockStateStore

  constructor(store?: MockStateStore) {
    this.store = store || new MockStateStore()
  }

  // 1. Availability
  async getAvailabilityMatrix(input: AvailabilityMatrixInput): Promise<AvailabilityMatrixResponse> {
    await LatencySimulator.inject('heavy')

    // Base equipment rows built from core catalog
    const baseRows = this.store.catalog.map((item) => {
      const itemSerials = this.store.serials.filter((s) => s.item_code === item.item_code)
      return {
        item_code: item.item_code,
        item_name: item.item_name,
        category: item.category,
        total_fleet: item.total_fleet_quantity,
        is_serialized: item.is_serialized,
        serials: itemSerials.map((s) => {
          const blocks = []

          // DEMO-SN-ALX-001: Checked Out
          if (s.serial_number === 'DEMO-SN-ALX-001') {
            blocks.push({
              id: `blk-${s.serial_number}-chk`,
              rental_id: 'DEMO-TRX-2026-001',
              rental_name: 'DEMO-TRX-2026-001',
              customer_name: 'Production Nord Inc.',
              state: 'Checked Out' as const,
              start_date: '2026-09-01T08:00:00Z',
              end_date: '2026-09-08T18:00:00Z',
              is_conflict: false
            })
          }

          // DEMO-SN-ALX-002: Real Conflict (Reservation overlaps Contract)
          if (s.serial_number === 'DEMO-SN-ALX-002') {
            blocks.push({
              id: `blk-${s.serial_number}-cnt`,
              rental_id: 'DEMO-TRX-2026-006',
              rental_name: 'DEMO-TRX-2026-006',
              customer_name: 'Production Nord Inc.',
              state: 'Contract' as const,
              start_date: '2026-09-08T08:00:00Z',
              end_date: '2026-09-15T18:00:00Z',
              is_conflict: true,
              conflict_reason: 'Chevauchement temporel détecté avec Réservation DEMO-TRX-2026-002'
            })
            blocks.push({
              id: `blk-${s.serial_number}-res`,
              rental_id: 'DEMO-TRX-2026-002',
              rental_name: 'DEMO-TRX-2026-002',
              customer_name: 'Studio Lumière Montréal',
              state: 'Reservation' as const,
              start_date: '2026-09-10T08:00:00Z',
              end_date: '2026-09-17T18:00:00Z',
              is_conflict: true,
              conflict_reason: 'Double réservation : Contrat DEMO-TRX-2026-006 actif sur la même plage horaire'
            })
          }

          // DEMO-SN-ALX-004: Quarantine
          if (s.serial_number === 'DEMO-SN-ALX-004') {
            blocks.push({
              id: `blk-${s.serial_number}-qur`,
              rental_id: 'DEMO-TRX-2026-004',
              rental_name: 'DEMO-TRX-2026-004',
              customer_name: 'Production Nord Inc.',
              state: 'Quarantine' as const,
              start_date: '2026-09-01T17:30:00Z',
              end_date: '2026-09-07T18:00:00Z',
              is_conflict: false,
              conflict_reason: 'Quarantaine : poussière capteur et révision'
            })
          }

          // DEMO-SN-CKE-101: Checked Out
          if (s.serial_number === 'DEMO-SN-CKE-101') {
            blocks.push({
              id: `blk-${s.serial_number}-chk`,
              rental_id: 'DEMO-TRX-2026-001',
              rental_name: 'DEMO-TRX-2026-001',
              customer_name: 'Production Nord Inc.',
              state: 'Checked Out' as const,
              start_date: '2026-09-01T08:00:00Z',
              end_date: '2026-09-08T18:00:00Z',
              is_conflict: false
            })
          }

          // DEMO-SN-CKE-102: Contract
          if (s.serial_number === 'DEMO-SN-CKE-102') {
            blocks.push({
              id: `blk-${s.serial_number}-cnt`,
              rental_id: 'DEMO-TRX-2026-006',
              rental_name: 'DEMO-TRX-2026-006',
              customer_name: 'Production Nord Inc.',
              state: 'Contract' as const,
              start_date: '2026-09-08T08:00:00Z',
              end_date: '2026-09-15T18:00:00Z',
              is_conflict: false
            })
          }

          return {
            serial_number: s.serial_number,
            status: s.status,
            blocks
          }
        }),
        blocks: item.item_code === 'DEMO-ITM-VRP8K'
          ? [
              {
                id: 'blk-VRP-qte',
                rental_id: 'DEMO-TRX-2026-003',
                rental_name: 'DEMO-TRX-2026-003',
                customer_name: 'Trequista Events',
                state: 'Quote' as const,
                start_date: '2026-09-15T08:00:00Z',
                end_date: '2026-09-18T18:00:00Z',
                is_conflict: false
              }
            ]
          : []
      }
    })

    // Generate 100+ rows dataset for virtualization testing and full fleet demo
    const categories = ['Cameras', 'Lenses', 'Lighting', 'Grip', 'Audio', 'Monitoring', 'Power & Batteries']
    const generatedFleetRows = []
    const totalTargetRows = 105

    for (let i = baseRows.length + 1; i <= totalTargetRows; i++) {
      const padIndex = String(i).padStart(3, '0')
      const cat = categories[i % categories.length] || 'Accessories'
      const isSer = i % 3 !== 0
      const itemCode = `DEMO-FLT-${padIndex}`
      const itemName = `${cat} Unit #${padIndex} (Pro Series)`

      const serials = isSer
        ? [
            {
              serial_number: `DEMO-SN-FLT-${padIndex}-A`,
              status: i % 7 === 0 ? 'Checked Out' : 'Available',
              blocks: i % 7 === 0
                ? [
                    {
                      id: `blk-flt-${padIndex}-a`,
                      rental_id: 'DEMO-TRX-2026-001',
                      rental_name: 'DEMO-TRX-2026-001',
                      customer_name: 'Production Nord Inc.',
                      state: 'Checked Out' as const,
                      start_date: '2026-09-01T08:00:00Z',
                      end_date: '2026-09-08T18:00:00Z',
                      is_conflict: false
                    }
                  ]
                : []
            },
            {
              serial_number: `DEMO-SN-FLT-${padIndex}-B`,
              status: i % 11 === 0 ? 'Quarantine' : 'Available',
              blocks: i % 11 === 0
                ? [
                    {
                      id: `blk-flt-${padIndex}-b`,
                      rental_id: 'DEMO-TRX-2026-004',
                      rental_name: 'DEMO-TRX-2026-004',
                      customer_name: 'Production Nord Inc.',
                      state: 'Quarantine' as const,
                      start_date: '2026-09-01T08:00:00Z',
                      end_date: '2026-09-06T18:00:00Z',
                      is_conflict: false
                    }
                  ]
                : []
            }
          ]
        : []

      generatedFleetRows.push({
        item_code: itemCode,
        item_name: itemName,
        category: cat,
        total_fleet: isSer ? serials.length : 10,
        is_serialized: isSer,
        serials,
        blocks: !isSer && i % 5 === 0
          ? [
              {
                id: `blk-flt-qty-${padIndex}`,
                rental_id: 'DEMO-TRX-2026-002',
                rental_name: 'DEMO-TRX-2026-002',
                customer_name: 'Studio Lumière Montréal',
                state: 'Reservation' as const,
                start_date: '2026-09-10T08:00:00Z',
                end_date: '2026-09-17T18:00:00Z',
                is_conflict: false
              }
            ]
          : []
      })
    }

    let allRows = [...baseRows, ...generatedFleetRows]

    // Apply category and search filters if supplied
    if (input.category && input.category !== 'all') {
      allRows = allRows.filter((r) => r.category.toLowerCase() === input.category?.toLowerCase())
    }
    if (input.search && input.search.trim() !== '') {
      const q = input.search.toLowerCase()
      allRows = allRows.filter((r) => r.item_name.toLowerCase().includes(q) || r.item_code.toLowerCase().includes(q))
    }

    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      start_date: input.start_date,
      end_date: input.end_date,
      rows: allRows
    }
  }

  async checkInventoryAvailability(input: AvailabilityCheckInput): Promise<AvailabilityCheckResponse> {
    await LatencySimulator.inject('fast')
    let allAvailable = true
    const items = input.items.map((req) => {
      const item = this.store.catalog.find((c) => c.item_code === req.item_code)
      const available = item ? item.available_quantity : 0
      const isAvail = available >= req.quantity
      if (!isAvail) allAvailable = false
      return {
        item_code: req.item_code,
        requested_quantity: req.quantity,
        available_quantity: available,
        is_available: isAvail
      }
    })

    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      all_available: allAvailable,
      items
    }
  }

  async getAvailabilityAlternatives(input: AlternativesInput): Promise<AlternativesResponse> {
    await LatencySimulator.inject('standard')
    const targetItem = this.store.catalog.find((c) => c.item_code === input.item_code)
    const category = targetItem?.category || 'Cameras'
    const alternatives = this.store.catalog
      .filter((c) => c.category === category && c.item_code !== input.item_code)
      .map((c) => ({
        item_code: c.item_code,
        item_name: c.item_name,
        daily_rate: c.daily_rate,
        available_quantity: c.available_quantity,
        match_score: 0.88,
        specification_diff: `Alternative équivalente dans la catégorie ${category}`
      }))

    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      item_code: input.item_code,
      alternatives
    }
  }

  // 2. Rentals Lifecycle & Pricing
  async listRentals(input: ListRentalsInput): Promise<ListRentalsResponse> {
    await LatencySimulator.inject('standard')
    let list = [...this.store.rentals]
    if (input.state) {
      list = list.filter((r) => r.rental_state === input.state)
    }
    if (input.search) {
      const q = input.search.toLowerCase()
      list = list.filter((r) => r.id.toLowerCase().includes(q) || r.customer_name.toLowerCase().includes(q))
    }

    const page = input.page || 1
    const pageSize = input.page_size || 20
    const startIdx = (page - 1) * pageSize
    const paginated = list.slice(startIdx, startIdx + pageSize)

    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      items: paginated,
      total_count: list.length,
      page,
      page_size: pageSize,
      total_pages: Math.ceil(list.length / pageSize) || 1
    }
  }

  async getRental(input: GetRentalInput): Promise<GetRentalResponse> {
    await LatencySimulator.inject('standard')
    const rental = this.store.rentals.find((r) => r.id === input.id || r.name === input.id)
    if (!rental) {
      throw new Error(`Location introuvable: ${input.id}`)
    }
    return { ...rental, provenance: 'mock', last_synced_at: new Date().toISOString() }
  }

  async searchRentalCustomers(query: string): Promise<RentalCustomerOption[]> {
    const needle = query.trim().toLowerCase()
    return this.store.customers
      .filter(customer => !needle || customer.name.toLowerCase().includes(needle) || customer.id.toLowerCase().includes(needle))
      .map(customer => ({
        id: customer.id,
        name: customer.name,
        insurance_valid: customer.insurance_valid_until >= new Date().toISOString().slice(0, 10)
      }))
  }

  async searchRentalCatalog(query: string): Promise<RentalCatalogOption[]> {
    const needle = query.trim().toLowerCase()
    return this.store.catalog
      .filter(item => !needle || item.item_name.toLowerCase().includes(needle) || item.item_code.toLowerCase().includes(needle))
      .map(item => ({
        item_code: item.item_code,
        item_name: item.item_name,
        category: item.category,
        daily_rate: item.daily_rate,
        is_serialized: item.is_serialized,
        required_accessories: item.required_accessories || []
      }))
  }

  async previewPricing(input: PreviewPricingInput): Promise<PreviewPricingResponse> {
    await LatencySimulator.inject('fast')
    const start = new Date(input.starts_at)
    const end = new Date(input.ends_at)
    const diffDays = Math.max(1, Math.round((end.getTime() - start.getTime()) / (1000 * 3600 * 24)))
    
    // Piecewise weekly formula: (weeks * 3) + Math.min(remainder, 3)
    const billableDays = calculateBillableDays(diffDays)
    
    let subtotal = 0
    let totalDiscount = 0
    const lines = input.items.map((item) => {
      const catItem = this.store.catalog.find((c) => c.item_code === item.item_code)
      const rate = item.daily_rate || catItem?.daily_rate || 1000
      const discount = item.discount_percentage || 0
      const lineTotal = rate * billableDays * item.quantity * (1 - discount / 100)
      const lineDisc = rate * billableDays * item.quantity * (discount / 100)
      subtotal += rate * billableDays * item.quantity
      totalDiscount += lineDisc
      return {
        item_code: item.item_code,
        daily_rate: rate,
        billable_days: billableDays,
        line_subtotal: lineTotal
      }
    })

    const netSubtotal = subtotal - totalDiscount
    // DEMO template: TPS 5 % + TVQ 9,975 % (the real template comes from ERPNext).
    const taxLines = [
      { description: 'TPS (DEMO)', rate: 5, amount: Number((netSubtotal * 0.05).toFixed(2)) },
      { description: 'TVQ (DEMO)', rate: 9.975, amount: Number((netSubtotal * 0.09975).toFixed(2)) }
    ]
    const taxAmount = Number(taxLines.reduce((sum, line) => sum + line.amount, 0).toFixed(2))
    const grandTotal = Number((netSubtotal + taxAmount).toFixed(2))

    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      calendar_days: diffDays,
      billable_days: billableDays,
      subtotal,
      discount_amount: totalDiscount,
      tax_amount: taxAmount,
      tax_lines: taxLines,
      tax_template: 'DEMO TPS/TVQ',
      tax_estimate_complete: true,
      grand_total: grandTotal,
      pricing_rule_applied: diffDays % 7 === 0 ? 'Règle standard 7 jours = 3 jours facturés' : 'Tarification dégressive standard',
      lines
    }
  }

  async createQuoteDraft(input: CreateQuoteDraftInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const reqId = `req-quote-${Date.now()}`
    const injected = ErrorInjector.checkAndInject(reqId)
    if (injected) return injected

    const newId = `DEMO-TRX-2026-${String(this.store.rentals.length + 1).padStart(3, '0')}`
    const customer = this.store.customers.find((c) => c.id === input.customer_id)
    const custName = customer?.name || 'Client Démonstration'

    const start = new Date(input.starts_at)
    const end = new Date(input.ends_at)
    const calendarDays = Math.max(1, Math.round((end.getTime() - start.getTime()) / (1000 * 3600 * 24)))
    const billableDays = calculateBillableDays(calendarDays)

    const lines: RentalLineItem[] = input.items.map((it, idx) => {
      const cat = this.store.catalog.find((c) => c.item_code === it.item_code)
      const rate = cat?.daily_rate || 1000
      const discount = it.discount_percentage || 0
      const lineSubtotal = rate * billableDays * it.quantity * (1 - discount / 100)
      return {
        id: `DEMO-LINE-${Date.now()}-${idx}`,
        item_code: it.item_code,
        item_name: cat?.item_name || it.item_code,
        category: cat?.category || 'General',
        quantity: it.quantity,
        daily_rate: rate,
        discount_percentage: discount,
        billable_days: billableDays,
        subtotal: lineSubtotal,
        assigned_serials: [],
        scanned_checkout_serials: [],
        scanned_checkin_serials: [],
        is_consigned: false
      }
    })

    const subtotal = lines.reduce((acc, l) => acc + l.subtotal, 0)
    const newRental: RentalTransaction = {
      available_actions: demoActions('Quote'),
      provenance: 'demo',
      last_synced_at: new Date().toISOString(),
      version: 1,
      id: newId,
      name: newId,
      company: 'DEMO-COMP-001',
      customer_id: input.customer_id,
      customer_name: custName,
      project_name: input.project_name || 'Nouveau Projet',
      rental_state: 'Quote',
      starts_at: input.starts_at,
      ends_at: input.ends_at,
      calendar_days: calendarDays,
      billable_days: billableDays,
      subtotal,
      discount_total: 0,
      tax_rate: 0.14975,
      tax_amount: Number((subtotal * 0.14975).toFixed(2)),
      grand_total: Number((subtotal * 1.14975).toFixed(2)),
      currency: 'CAD',
      readiness: {
        customer_account_ready: true,
        insurance_ready: customer ? customer.insurance_coverage_cad > 0 : true,
        payment_ready: true,
        overall_ready: customer ? customer.insurance_coverage_cad > 0 : true,
        missing_requirements: []
      },
      items: lines,
      notes: input.notes,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    this.store.rentals.unshift(newRental)
    const auditId = this.store.recordAudit(
      'cortex.rental.quote_created',
      'Cortex Rental Transaction',
      newId,
      'kael@cortex.local',
      'Human',
      `Création du devis ${newId} pour ${custName}`
    )

    return {
      request_id: reqId,
      entity_id: newId,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async updateQuoteDraft(input: UpdateQuoteDraftInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const reqId = `req-upd-quote-${Date.now()}`
    const injected = ErrorInjector.checkAndInject(reqId)
    if (injected) return injected

    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: reqId,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: `Location ${input.rental_id} introuvable.` }]
      }
    }

    if (rental.version !== input.version) {
      return {
        request_id: reqId,
        status: 'stale',
        stale_context: true,
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'CONCURRENCY_ERROR', message: 'La ressource a été modifiée par un autre utilisateur.' }]
      }
    }

    if (input.starts_at) rental.starts_at = input.starts_at
    if (input.ends_at) rental.ends_at = input.ends_at
    if (input.project_name) rental.project_name = input.project_name
    if (input.notes) rental.notes = input.notes
    rental.version += 1
    rental.updated_at = new Date().toISOString()

    const auditId = this.store.recordAudit(
      'cortex.rental.quote_updated',
      'Cortex Rental Transaction',
      rental.id,
      'kael@cortex.local',
      'Human',
      `Mise à jour du devis ${rental.id}`
    )

    return {
      request_id: reqId,
      entity_id: rental.id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async requestReservation(input: RequestReservationInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const reqId = `req-resa-${Date.now()}`
    const injected = ErrorInjector.checkAndInject(reqId)
    if (injected) return injected

    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: reqId,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: `Location ${input.rental_id} introuvable.` }]
      }
    }

    if (input.version !== undefined && rental.version !== input.version) {
      return {
        request_id: reqId,
        status: 'stale',
        stale_context: true,
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'CONCURRENCY_ERROR', message: 'La ressource a été modifiée par un autre utilisateur.' }]
      }
    }

    if (rental.rental_state !== 'Quote') {
      return {
        request_id: reqId,
        status: 'policy_denied',
        approval_required: false,
        mutation_performed: false,
        policy_result: {
          policy_name: 'cortex.reservation.quote_required',
          explanation: `La réservation nécessite une soumission ou un brouillon. État actuel: ${rental.rental_state}`
        },
        errors: [{ code: 'INVALID_STATE', message: `Impossible de réserver une location en état '${rental.rental_state}'.` }]
      }
    }

    rental.rental_state = 'Reservation'
    rental.version += 1
    rental.updated_at = new Date().toISOString()

    const auditId = this.store.recordAudit(
      'cortex.rental.reservation_confirmed',
      'Cortex Rental Transaction',
      rental.id,
      'kael@cortex.local',
      'Human',
      `Passage en statut Réservation pour ${rental.id}`
    )

    return {
      request_id: reqId,
      entity_id: rental.id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async requestContractApproval(input: RequestContractApprovalInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const reqId = `req-contract-appr-${Date.now()}`
    const injected = ErrorInjector.checkAndInject(reqId)
    if (injected) return injected

    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: reqId,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: `Location ${input.rental_id} introuvable.` }]
      }
    }

    if (input.version !== undefined && rental.version !== input.version) {
      return {
        request_id: reqId,
        status: 'stale',
        stale_context: true,
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'CONCURRENCY_ERROR', message: 'La ressource a été modifiée par un autre utilisateur.' }]
      }
    }

    if (rental.rental_state !== 'Reservation' && rental.rental_state !== 'Quote') {
      return {
        request_id: reqId,
        status: 'policy_denied',
        approval_required: false,
        mutation_performed: false,
        policy_result: {
          policy_name: 'cortex.contract.state_required',
          explanation: `Le contrat exige l'état Reservation ou Quote. État actuel: ${rental.rental_state}`
        },
        errors: [{ code: 'INVALID_STATE', message: `Impossible de demander un contrat pour l'état '${rental.rental_state}'.` }]
      }
    }

    if (!rental.readiness.overall_ready && !input.override_reason) {
      const approvalId = `DEMO-APR-${String(this.store.approvals.length + 1).padStart(3, '0')}`
      this.store.approvals.unshift({
        provenance: 'demo',
        last_synced_at: new Date().toISOString(),
        id: approvalId,
        approval_type: 'Contract Confirmation',
        status: 'pending',
        title: `Validation Contrat avec exigences manquantes — ${rental.customer_name}`,
        description: `Exigences: ${rental.readiness.missing_requirements.join(', ')}`,
        reference_doctype: 'Cortex Rental Transaction',
        reference_name: rental.id,
        requested_by_type: 'Human',
        requested_by: 'kael@cortex.local',
        created_at: new Date().toISOString()
      })

      return {
        request_id: reqId,
        entity_id: rental.id,
        status: 'approval_required',
        approval_required: true,
        approval_request_id: approvalId,
        mutation_performed: false,
        policy_result: {
          policy_name: 'Rental Contract Readiness Policy',
          explanation: 'La transaction comporte des conditions non remplies.',
          next_allowed_action: 'Soumis à la file d’approbation du superviseur.'
        }
      }
    }

    rental.rental_state = 'Contract'
    rental.version += 1
    rental.updated_at = new Date().toISOString()

    const auditId = this.store.recordAudit(
      'cortex.rental.contract_approved',
      'Cortex Rental Transaction',
      rental.id,
      'kael@cortex.local',
      'Human',
      `Contrat confirmé pour ${rental.id}`
    )

    return {
      request_id: reqId,
      entity_id: rental.id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async getRentalAudit(input: GetRentalAuditInput): Promise<GetRentalAuditResponse> {
    await LatencySimulator.inject('standard')
    const events = this.store.auditEvents
      .filter((e) => e.entity_id === input.rental_id)
      .map((e) => ({
        id: e.id,
        timestamp: e.timestamp,
        actor: {
          actor_type: e.actor.actor_type,
          actor_id: e.actor.actor_id
        },
        action: e.action,
        diff_summary: e.diff_summary
      }))

    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      rental_id: input.rental_id,
      events
    }
  }

  // 3. Warehouse Operations
  async startCheckout(input: StartCheckoutInput): Promise<MutationResponse> {
    await LatencySimulator.inject('fast')
    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: `req-chk-start-${Date.now()}`,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: `Location ${input.rental_id} introuvable.` }]
      }
    }
    if (rental.rental_state !== 'Contract' && rental.rental_state !== 'Reservation') {
      return {
        request_id: `req-chk-start-${Date.now()}`,
        status: 'policy_denied',
        approval_required: false,
        mutation_performed: false,
        policy_result: {
          policy_name: 'cortex.checkout.contract_required',
          explanation: `Le checkout exige un contrat validé ou une réservation confirmée. État actuel: ${rental.rental_state}`
        },
        errors: [{ code: 'INVALID_TRANSITION', message: `Sortie interdite pour l'état ${rental.rental_state}. Une réservation ou un contrat est requis.` }]
      }
    }
    return {
      request_id: `req-chk-start-${Date.now()}`,
      entity_id: input.rental_id,
      status: 'completed',
      approval_required: false,
      mutation_performed: true
    }
  }

  async scanCheckoutSerial(input: ScanCheckoutSerialInput): Promise<MutationResponse> {
    await LatencySimulator.inject('fast')
    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: `req-scan-${Date.now()}`,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: 'Location introuvable.' }]
      }
    }

    // Assign/scan serial
    let matched = false
    for (const item of rental.items) {
      if (!item.scanned_checkout_serials.includes(input.serial_number)) {
        item.scanned_checkout_serials.push(input.serial_number)
        matched = true
        break
      }
    }

    const auditId = this.store.recordAudit(
      'cortex.scanner.checkout_item',
      'Serial Number',
      input.serial_number,
      'kael@cortex.local',
      'Human',
      `Scan sortie du numéro de série ${input.serial_number} sur ${rental.id}`
    )

    return {
      request_id: `req-scan-${Date.now()}`,
      entity_id: rental.id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: matched
    }
  }

  async completeCheckout(input: CompleteCheckoutInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: `req-chk-complete-${Date.now()}`,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: `Location ${input.rental_id} introuvable.` }]
      }
    }
    if (rental.rental_state !== 'Contract' && rental.rental_state !== 'Reservation') {
      return {
        request_id: `req-chk-complete-${Date.now()}`,
        status: 'policy_denied',
        approval_required: false,
        mutation_performed: false,
        policy_result: {
          policy_name: 'cortex.checkout.contract_required',
          explanation: `Le checkout exige un contrat validé ou une réservation confirmée. État actuel: ${rental.rental_state}`
        },
        errors: [{ code: 'INVALID_TRANSITION', message: `Sortie interdite pour l'état ${rental.rental_state}. Une réservation ou un contrat est requis.` }]
      }
    }
    rental.rental_state = 'Checked Out'
    rental.version += 1
    rental.updated_at = new Date().toISOString()

    const auditId = this.store.recordAudit(
      'cortex.rental.checkout_completed',
      'Cortex Rental Transaction',
      input.rental_id,
      'kael@cortex.local',
      'Human',
      `Expédition et sortie d’équipement validées pour ${input.rental_id}`
    )

    return {
      request_id: `req-chk-complete-${Date.now()}`,
      entity_id: input.rental_id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async startCheckin(input: StartCheckinInput): Promise<MutationResponse> {
    await LatencySimulator.inject('fast')
    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: `req-chkin-start-${Date.now()}`,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: `Location ${input.rental_id} introuvable.` }]
      }
    }
    if (rental.rental_state !== 'Checked Out') {
      return {
        request_id: `req-chkin-start-${Date.now()}`,
        status: 'policy_denied',
        approval_required: false,
        mutation_performed: false,
        policy_result: {
          policy_name: 'cortex.checkin.status_required',
          explanation: `Le check-in exige un équipement sorti (Checked Out / Partially Returned). État actuel: ${rental.rental_state}`
        },
        errors: [{ code: 'INVALID_STATE', message: `Check-in interdit pour l'état ${rental.rental_state}.` }]
      }
    }
    return {
      request_id: `req-chkin-start-${Date.now()}`,
      entity_id: input.rental_id,
      status: 'completed',
      approval_required: false,
      mutation_performed: true
    }
  }

  async scanCheckinSerial(input: ScanCheckinSerialInput): Promise<MutationResponse> {
    await LatencySimulator.inject('fast')
    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: `req-chkin-scan-${Date.now()}`,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: 'Location introuvable.' }]
      }
    }

    for (const item of rental.items) {
      if (!item.scanned_checkin_serials.includes(input.serial_number)) {
        item.scanned_checkin_serials.push(input.serial_number)
        break
      }
    }

    const auditId = this.store.recordAudit(
      'cortex.scanner.checkin_item',
      'Serial Number',
      input.serial_number,
      'kael@cortex.local',
      'Human',
      `Retour du numéro de série ${input.serial_number} (État: ${input.condition})`
    )

    return {
      request_id: `req-chkin-scan-${Date.now()}`,
      entity_id: rental.id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async markSerialMissing(input: MarkSerialMissingInput): Promise<MutationResponse> {
    await LatencySimulator.inject('fast')
    const serial = this.store.serials.find((s) => s.serial_number === input.serial_number)
    if (serial) {
      serial.status = 'Missing'
    }

    const auditId = this.store.recordAudit(
      'cortex.scanner.serial_marked_missing',
      'Serial Number',
      input.serial_number,
      'kael@cortex.local',
      'Human',
      `Équipement ${input.serial_number} déclaré manquant au retour: ${input.reason}`
    )

    return {
      request_id: `req-missing-${Date.now()}`,
      entity_id: input.serial_number,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async addDamageEvidence(input: AddDamageEvidenceInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const serial = this.store.serials.find((s) => s.serial_number === input.serial_number)
    if (serial) {
      serial.status = input.severity === 'unusable' ? 'Quarantine' : 'Repair'
    }

    const auditId = this.store.recordAudit(
      'cortex.scanner.damage_evidence_added',
      'Serial Number',
      input.serial_number,
      'kael@cortex.local',
      'Human',
      `Preuve de dommage enregistrée (${input.severity}): ${input.description}`
    )

    return {
      request_id: `req-dmg-${Date.now()}`,
      entity_id: input.serial_number,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async completePartialReturn(input: CompletePartialReturnInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const rental = this.store.rentals.find((r) => r.id === input.rental_id)
    if (!rental) {
      return {
        request_id: `req-partial-${Date.now()}`,
        status: 'failed',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'NOT_FOUND', message: `Location ${input.rental_id} introuvable.` }]
      }
    }
    if (rental.rental_state !== 'Checked Out') {
      return {
        request_id: `req-partial-${Date.now()}`,
        status: 'policy_denied',
        approval_required: false,
        mutation_performed: false,
        policy_result: {
          policy_name: 'cortex.checkin.status_required',
          explanation: `Le retour partiel exige l'état Checked Out. État actuel: ${rental.rental_state}`
        },
        errors: [{ code: 'INVALID_STATE', message: `Retour partiel interdit pour l'état '${rental.rental_state}'.` }]
      }
    }
    // A partial return keeps the rental Checked Out (same as the server).
    rental.rental_state = 'Checked Out'
    rental.version += 1
    rental.updated_at = new Date().toISOString()

    const auditId = this.store.recordAudit(
      'cortex.rental.partial_return_completed',
      'Cortex Rental Transaction',
      input.rental_id,
      'kael@cortex.local',
      'Human',
      `Retour partiel enregistré pour ${input.rental_id}. Équipements restants maintenus hors-location.`
    )

    return {
      request_id: `req-partial-${Date.now()}`,
      entity_id: input.rental_id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async lookupScan(input: LookupScanInput): Promise<LookupScanResponse> {
    await LatencySimulator.inject('fast')
    const serial = this.store.serials.find((s) => s.serial_number === input.barcode)
    if (serial) {
      return {
        provenance: 'mock',
        last_synced_at: new Date().toISOString(),
        barcode: input.barcode,
        entity_type: 'serial_number',
        entity_id: serial.serial_number,
        display_title: `${serial.item_name} (${serial.serial_number})`,
        current_status: serial.status,
        associated_rental_id: serial.status === 'Checked Out' ? 'DEMO-TRX-2026-001' : undefined
      }
    }

    const item = this.store.catalog.find((c) => c.item_code === input.barcode)
    if (item) {
      return {
        provenance: 'mock',
        last_synced_at: new Date().toISOString(),
        barcode: input.barcode,
        entity_type: 'item',
        entity_id: item.item_code,
        display_title: item.item_name,
        current_status: `${item.available_quantity} / ${item.total_fleet_quantity} disponibles`
      }
    }

    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      barcode: input.barcode,
      entity_type: 'unknown',
      display_title: 'Code-barres non répertorié',
      current_status: 'Inconnu'
    }
  }

  // 4. Consignment & Owner Statements (Strict Anti-PII Guarantee)
  // Consignment: DEMO data mapped to the server shapes (explicit mock mode only).
  private demoOwnerRow(o: (typeof this.store.owners)[number]): ConsignmentOwner {
    const pending = this.store.consignmentDashboard.pending_statements.find(p => p.owner_id === o.id)
    return {
      id: o.id, owner_code: o.owner_code, display_name: o.display_name, owner_type: 'Third-Party', contact_email: o.contact_email,
      contact_phone: o.contact_phone ?? '', default_commission_percentage: o.default_commission_percentage, active_serials_count: o.active_serials_count,
      period_revenue: Math.round(o.pending_payout_amount / (o.default_commission_percentage / 100)), period_amount_due: o.pending_payout_amount,
      statement_status: pending ? pending.status : 'not_prepared'
    }
  }

  async listOwners(input: ListOwnersInput): Promise<ListOwnersResponse> {
    await LatencySimulator.inject('fast')
    const q = (input.search ?? '').toLowerCase()
    const items = this.store.owners.filter(o => !q || o.display_name.toLowerCase().includes(q) || o.owner_code.toLowerCase().includes(q)).map(o => this.demoOwnerRow(o))
    return { provenance: 'mock', items, total_count: items.length }
  }

  async getConsignmentDashboard(input: ConsignmentDashboardInput): Promise<ConsignmentDashboardResponse> {
    await LatencySimulator.inject('fast')
    const d = this.store.consignmentDashboard
    return {
      provenance: 'mock', period: input.period ?? '2026-08', currency: 'CAD',
      current_month_total_payout: d.current_month_total_payout, previous_month_total_payout: d.previous_month_total_payout,
      active_owners_count: d.active_owners_count, active_consigned_serials_count: d.active_consigned_serials_count,
      owners: this.store.owners.map(o => this.demoOwnerRow(o)),
      top_earning_items: d.top_earning_items.map(item => ({ serial_number: item.item_code, item_name: item.item_name, owner_code: item.owner_code, revenue_generated: item.revenue_generated, owner_payout: item.owner_payout }))
    }
  }

  async getOwnerStatement(input: OwnerStatementInput): Promise<OwnerStatementResponse> {
    await LatencySimulator.inject('fast')
    const statement = this.store.ownerStatements[`${input.owner_id}_${input.period}`]
    if (!statement) throw new Error(`Relevé propriétaire introuvable pour ${input.owner_id} (${input.period})`)
    const pending = this.store.consignmentDashboard.pending_statements.find(p => p.owner_id === input.owner_id && p.period === input.period)
    return { provenance: 'mock', last_synced_at: new Date().toISOString(), statement, status: pending?.status ?? 'not_prepared' }
  }

  // 5. Approvals
  async listApprovalRequests(input: ListApprovalRequestsInput): Promise<ListApprovalsResponse> {
    await LatencySimulator.inject('standard')
    let list = [...this.store.approvals]
    if (input.status) {
      list = list.filter((a) => a.status === input.status)
    }
    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      items: list,
      total_count: list.length
    }
  }

  async getApprovalRequest(input: GetApprovalRequestInput): Promise<GetApprovalResponse> {
    await LatencySimulator.inject('standard')
    const req = this.store.approvals.find((a) => a.id === input.id)
    if (!req) {
      throw new Error(`Demande d'approbation introuvable: ${input.id}`)
    }
    return { ...req, provenance: 'mock', last_synced_at: new Date().toISOString() }
  }

  async approveApprovalRequest(input: ApproveApprovalInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const req = this.store.approvals.find((a) => a.id === input.id)
    if (req) {
      req.status = 'approved'
      req.resolved_at = new Date().toISOString()
      req.resolved_by = 'kael@cortex.local'
    }

    const auditId = this.store.recordAudit(
      'cortex.approval.request_approved',
      'Approval Request',
      input.id,
      'kael@cortex.local',
      'Human',
      `Demande d'approbation ${input.id} validée par l’opérateur.`
    )

    return {
      request_id: `req-appr-${Date.now()}`,
      entity_id: input.id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  async rejectApprovalRequest(input: RejectApprovalInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const req = this.store.approvals.find((a) => a.id === input.id)
    if (req) {
      req.status = 'rejected'
      req.resolved_at = new Date().toISOString()
      req.resolved_by = 'kael@cortex.local'
      req.rejection_reason = input.reason
    }

    const auditId = this.store.recordAudit(
      'cortex.approval.request_rejected',
      'Approval Request',
      input.id,
      'kael@cortex.local',
      'Human',
      `Demande d'approbation ${input.id} rejetée: ${input.reason}`
    )

    return {
      request_id: `req-rej-${Date.now()}`,
      entity_id: input.id,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  // 6. AI (DEMO data in the server shapes; explicit mock mode only)
  async listInbox(kind?: InboxKind, includeClosed = false): Promise<InboxList> {
    await LatencySimulator.inject('standard')
    const closed = new Set(['validated', 'rejected', 'applied', 'expired'])
    const items = this.store.inbox.filter(item => (!kind || item.kind === kind) && (includeClosed || !closed.has(item.state)))
    return { provenance: 'mock', items, can_decide_approvals: true, team_scope_available: false }
  }

  async getInboxItem(kind: InboxKind, sourceId: string): Promise<InboxDetail> {
    await LatencySimulator.inject('standard')
    if (kind === 'inbound') {
      const detail = this.store.inboundDetails.find(d => d.id === sourceId)
      if (!detail) throw new Error(`Demande entrante introuvable : ${sourceId}`)
      return detail
    }
    if (kind === 'draft') return { kind: 'draft', rental: await this.getRental({ id: sourceId }) }
    const row = this.store.inbox.find(item => item.kind === 'approval' && item.source_id === sourceId)
    const approval = this.store.approvals.find(a => a.id === sourceId)
    if (!row || !approval) throw new Error(`Approbation introuvable : ${sourceId}`)
    return {
      kind: 'approval',
      row,
      status: approval.status === 'pending' ? 'Pending' : approval.status === 'approved' ? 'Approved' : approval.status === 'rejected' ? 'Rejected' : 'Expired',
      entity_type: approval.reference_doctype,
      entity_id: approval.reference_name,
      proposed: approval.after_state ?? {},
      current: approval.before_state ?? {},
      evidence_ids: approval.evidence_ids ?? [],
      policy_decision: approval.threshold_exceeded_details ? { reason: approval.threshold_exceeded_details } : {},
      decided_by: approval.resolved_by ?? null,
      decided_at: approval.resolved_at ?? null,
      decision_reason: approval.rejection_reason ?? null,
      self_requested: false
    }
  }

  async rejectInbound(sourceId: string, _reason: string): Promise<void> {
    await LatencySimulator.inject('fast')
    const row = this.store.inboxRows.find(item => item.kind === 'inbound' && item.source_id === sourceId)
    if (row) row.state = 'rejected'
  }

  async linkInboundToRental(sourceId: string, rentalId: string): Promise<void> {
    await LatencySimulator.inject('fast')
    const row = this.store.inboxRows.find(item => item.kind === 'inbound' && item.source_id === sourceId)
    if (row) row.state = 'applied'
    const detail = this.store.inboundDetails.find(d => d.id === sourceId)
    if (detail) detail.extracted_transaction = rentalId
  }

  async listAgentActivity(input: AgentActivityInput): Promise<AgentActivity> {
    await LatencySimulator.inject('standard')
    const items = this.store.agentRuns.filter(run => (!input.agent || run.agent === input.agent) && (!input.status || run.status === input.status))
    const start = (input.page - 1) * input.page_size
    return {
      provenance: 'mock',
      items: items.slice(start, start + input.page_size),
      total_count: items.length,
      page: input.page,
      page_size: input.page_size,
      agents: [...new Set(this.store.agentRuns.map(run => run.agent))].sort()
    }
  }

  // 7. Assistant — the mock never invents an answer: it says it is not connected.
  async getAssistantStatus(): Promise<AssistantStatus> {
    return { available: false, provider: 'mock', model_name: null }
  }

  async sendChatMessage(_input: SendChatInput): Promise<SendChatResult> {
    throw new Error('Assistant non configuré en mode démonstration.')
  }

  async getChatSession(sessionId: string): Promise<ChatSessionDetail> {
    return { name: sessionId, agent_profile: 'cortex-operations', state: 'Active', messages: [] }
  }

  async listChatSessions(): Promise<ChatSessionSummary[]> {
    return []
  }

  // 8. Catalog, Fleet, Policies, Audit & Migration
  // Catalog: DEMO data mapped to the server shapes (explicit mock mode only).
  private demoSerialStatus(status: string): SerialStatus {
    return ({ Repair: 'Under Repair', 'Under Repair': 'Under Repair', Missing: 'Missing', Quarantine: 'Quarantine', Decommissioned: 'Decommissioned' } as Record<string, SerialStatus>)[status] ?? 'Active'
  }

  async listEquipment(input: ListEquipmentInput): Promise<ListEquipmentResponse> {
    await LatencySimulator.inject('fast')
    const q = (input.search ?? '').toLowerCase()
    const rows = this.store.catalog
      .filter(e => (!input.category || e.category === input.category) && (!q || e.item_name.toLowerCase().includes(q) || e.item_code.toLowerCase().includes(q)))
      .map(e => ({
        item_code: e.item_code, item_name: e.item_name, category: e.category, daily_rate: e.daily_rate, replacement_value: e.daily_rate * 40,
        is_serialized: e.is_serialized, currency: 'CAD', fleet_total: e.total_fleet_quantity, fleet_active: e.available_quantity,
        fleet_out: e.rented_quantity, fleet_unavailable: e.maintenance_quantity
      }))
    return this.pageOf(rows, input.page, input.page_size)
  }

  async getEquipment(input: GetEquipmentInput): Promise<GetEquipmentResponse> {
    await LatencySimulator.inject('fast')
    const item = this.store.catalog.find(c => c.item_code === input.item_code)
    if (!item) throw new Error(`Équipement introuvable: ${input.item_code}`)
    const serials = this.store.serials.filter(s => s.item_code === item.item_code)
    const curveDays = [1, 2, 3, 4, 5, 7, 10, 14, 21, 30]
    const billable = (d: number) => (d === 1 ? 1 : d === 2 ? 1.5 : d === 3 ? 2 : d === 4 ? 2.5 : d <= 7 ? 3 : d <= 14 ? 6 : d <= 30 ? 10 : d * 0.4)
    return {
      provenance: 'mock', item_code: item.item_code, item_name: item.item_name, description: '', image: null, item_group: item.category, brand: item.brand ?? null,
      category: item.category, daily_rate: item.daily_rate, replacement_value: item.daily_rate * 40, deposit_required: item.daily_rate * 2, prep_hours: 2,
      is_serialized: item.is_serialized, total_quantity: item.total_fleet_quantity, is_consignment_allowed: serials.some(s => s.is_consigned),
      required_accessories: item.required_accessories ?? [], currency: 'CAD',
      fleet: { total: item.total_fleet_quantity, active: item.available_quantity, out: item.rented_quantity, unavailable: item.maintenance_quantity },
      serials: serials.map(s => ({ serial_no: s.serial_number, status: this.demoSerialStatus(s.status), current_rental: s.status === 'Checked Out' ? 'DEMO-TRX-2026-001' : null, warranty_expiry_date: null })),
      pricing_curve: curveDays.map(d => ({ calendar_days: d, billable_days: billable(d), price: billable(d) * item.daily_rate })),
      can_edit: true
    }
  }

  async getSerial(input: GetSerialInput): Promise<GetSerialResponse> {
    await LatencySimulator.inject('fast')
    const serial = this.store.serials.find(s => s.serial_number === input.serial_number)
    if (!serial) throw new Error(`Numéro de série introuvable: ${input.serial_number}`)
    return {
      provenance: 'mock', serial_no: serial.serial_number, item_code: serial.item_code, item_name: serial.item_name, erpnext_status: 'Active',
      status: this.demoSerialStatus(serial.status), warranty_expiry_date: null, current_rental: serial.status === 'Checked Out' ? 'DEMO-TRX-2026-001' : null,
      rentals: this.store.rentals.filter(r => r.items.some(i => i.assigned_serials.includes(serial.serial_number))).map(r => ({ name: r.id, customer: r.customer_name, rental_state: r.rental_state, starts_at: r.starts_at, ends_at: r.ends_at })),
      returns: [], status_history: [], can_change_status: true
    }
  }

  async listKits(input: ListKitsInput): Promise<ListKitsResponse> {
    await LatencySimulator.inject('fast')
    return this.demoKits.filter(kit => input.include_inactive || kit.is_active).map(kit => structuredClone(kit))
  }

  private demoKits: RentalKit[] = [
    { name: 'DEMO-KIT-00001', kit_name: 'Kit caméra A (DEMO)', is_active: true, discount_percentage: 10, description: 'Alexa 35 + série Cooke S4/i',
      items: [
        { item_code: 'DEMO-ITM-ALX35', item_name: 'ARRI Alexa 35 Camera Package', qty: 1, is_optional: false, daily_rate: 1500 },
        { item_code: 'DEMO-ITM-CKE-S4', item_name: 'Cooke S4/i Prime Lens Set', qty: 1, is_optional: false, daily_rate: 950 }
      ] }
  ]

  async updateEquipmentProfile(itemCode: string, changes: EquipmentProfileChanges): Promise<GetEquipmentResponse> {
    await LatencySimulator.inject('mutation')
    const item = this.store.catalog.find(c => c.item_code === itemCode)
    if (item && changes.daily_rate !== undefined) item.daily_rate = changes.daily_rate
    return this.getEquipment({ item_code: itemCode })
  }

  async setSerialStatus(serialNo: string, status: SerialStatus): Promise<GetSerialResponse> {
    await LatencySimulator.inject('mutation')
    const serial = this.store.serials.find(s => s.serial_number === serialNo)
    if (serial) serial.status = (status === 'Active' ? 'Available' : status === 'Under Repair' ? 'Repair' : status) as typeof serial.status
    return this.getSerial({ serial_number: serialNo })
  }

  async saveKit(kit: RentalKit): Promise<RentalKit> {
    await LatencySimulator.inject('mutation')
    const saved = { ...structuredClone(kit), name: kit.name ?? `DEMO-KIT-${String(this.demoKits.length + 1).padStart(5, '0')}` }
    this.demoKits = [...this.demoKits.filter(k => k.name !== saved.name), saved]
    return saved
  }

  async listRentalPolicies(_input: ListRentalPoliciesInput): Promise<ListRentalPoliciesResponse> {
    await LatencySimulator.inject('standard')
    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      policies: this.store.policies
    }
  }

  async getTeamRoles(_input: GetTeamRolesInput): Promise<TeamRolesResponse> {
    await LatencySimulator.inject('standard')
    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      roles: [
        {
          role_name: 'Operations Lead',
          description: 'Responsable de la planification, approbation des contrats et dérogations.',
          permissions: ['cortex:operations:manage', 'cortex:approvals:decide', 'cortex:quote:override'],
          assigned_users_count: 3
        },
        {
          role_name: 'Warehouse Tech',
          description: 'Préparation et validation des sorties et retours de matériel via le scanner.',
          permissions: ['cortex:checkout:perform', 'cortex:checkin:perform', 'cortex:serial:quarantine'],
          assigned_users_count: 8
        },
        {
          role_name: 'Finance Lead',
          description: 'Gestion de la facturation et des relevés de consignation propriétaires.',
          permissions: ['cortex:consignment:finance', 'cortex:invoicing:manage'],
          assigned_users_count: 2
        }
      ],
      service_accounts: [
        {
          account_name: 'cortex-onyx-agent-service',
          role: 'AI Agent Service Account',
          api_key_masked: 'ctx_live_••••••••••••9941',
          last_active: '2026-09-02T15:58:00Z'
        }
      ]
    }
  }

  async listMigrationBatches(_input: ListMigrationBatchesInput): Promise<MigrationBatchesResponse> {
    await LatencySimulator.inject('standard')
    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      batches: this.store.migrationBatches
    }
  }

  async listAuditEvents(input: ListAuditEventsInput): Promise<ListAuditEventsResponse> {
    await LatencySimulator.inject('standard')
    let list = [...this.store.auditEvents]
    if (input.entity_type) {
      list = list.filter((e) => e.entity_type === input.entity_type)
    }
    if (input.entity_id) {
      list = list.filter((e) => e.entity_id === input.entity_id)
    }
    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      events: list,
      total_count: list.length
    }
  }

  // 9. Upload & Evidence
  async createUploadIntent(input: CreateUploadIntentInput): Promise<UploadIntentResponse> {
    await LatencySimulator.inject('fast')
    const uploadId = `upl-${Date.now()}`
    return {
      provenance: 'mock',
      last_synced_at: new Date().toISOString(),
      upload_intent_id: uploadId,
      upload_url: `https://mock-storage.cortex.local/uploads/${uploadId}/${input.file_name}`,
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
      expected_hash_algorithm: 'SHA-256'
    }
  }

  async registerEvidence(input: RegisterEvidenceInput): Promise<MutationResponse> {
    await LatencySimulator.inject('mutation')
    const auditId = this.store.recordAudit(
      'cortex.evidence.registered',
      input.entity_doctype,
      input.entity_name,
      'kael@cortex.local',
      'Human',
      `Preuve numérique enregistrée (SHA-256: ${input.file_sha256.slice(0, 16)}...)`
    )

    return {
      request_id: `req-reg-evd-${Date.now()}`,
      entity_id: input.entity_name,
      status: 'completed',
      approval_required: false,
      audit_event_id: auditId,
      mutation_performed: true
    }
  }

  // 10. Finance (DEMO data, explicit mock mode only)
  async getPnlFilterOptions(): Promise<PnlFilterOptions> {
    await LatencySimulator.inject('fast')
    return structuredClone(demoPnlFilterOptions)
  }

  async getProfitAndLoss(_filters: PnlFilters): Promise<PnlReport> {
    await LatencySimulator.inject('fast')
    return demoProfitAndLoss()
  }

  // 11. Global search (DEMO data, explicit mock mode only)
  async globalSearch(query: string): Promise<GlobalSearchResponse> {
    await LatencySimulator.inject('fast')
    const needle = query.trim().toLowerCase()
    if (needle.length < 2) return { query, results: [] }
    const rentals = this.store.rentals
      .filter(rental => rental.id.toLowerCase().includes(needle) || rental.customer_name.toLowerCase().includes(needle))
      .slice(0, 5)
      .map(rental => ({ type: 'rental' as const, id: rental.id, title: rental.id, subtitle: `${rental.customer_name} · ${rental.rental_state}` }))
    return { query, results: rentals }
  }

  // 12. Billing (DEMO data, explicit mock mode only)
  private pageOf<T>(rows: T[], page: number, pageSize: number): PagedResult<T> {
    return { provenance: 'mock', items: rows.slice((page - 1) * pageSize, page * pageSize), total_count: rows.length, page, page_size: pageSize }
  }

  async listInvoices(input: ListInvoicesInput): Promise<PagedResult<InvoiceRow>> {
    await LatencySimulator.inject('fast')
    const needle = (input.search ?? '').toLowerCase()
    const rows = demoInvoices.filter(row =>
      (!input.status || row.status === input.status) &&
      (!needle || [row.name, row.customer_name, row.cortex_rental_transaction].some(value => value.toLowerCase().includes(needle)))
    )
    return this.pageOf(rows, input.page, input.page_size)
  }

  async listPayments(input: ListPaymentsInput): Promise<PagedResult<PaymentRow>> {
    await LatencySimulator.inject('fast')
    const needle = (input.search ?? '').toLowerCase()
    const rows = demoPayments.filter(row => !needle || [row.name, row.party_name, row.cortex_rental_transaction].some(value => value.toLowerCase().includes(needle)))
    return this.pageOf(rows, input.page, input.page_size)
  }

  async getRentalBilling(rentalId: string): Promise<RentalBilling> {
    await LatencySimulator.inject('fast')
    const payments = demoPayments.filter(row => row.cortex_rental_transaction === rentalId)
    const received = payments.filter(row => row.docstatus === 1).reduce((sum, row) => sum + row.paid_amount, 0)
    const invoice = demoInvoices.find(row => row.cortex_rental_transaction === rentalId)
    return {
      currency: 'CAD',
      sales_order: { name: `DEMO-SO-${rentalId.slice(-3)}`, status: 'To Deliver and Bill', docstatus: 1, grand_total: 5173.88, advance_paid: received, per_billed: invoice ? 100 : 0 },
      advance: { percentage_amount: 1552.16, guarantee_amount: 500, requested: 2052.16, received, covered: received >= 2052.16 },
      payments: payments.map(row => ({ name: row.name, docstatus: row.docstatus, posting_date: row.posting_date, paid_amount: row.paid_amount, mode_of_payment: row.mode_of_payment, reference_no: row.reference_no })),
      final_invoice: invoice ? { name: invoice.name, status: invoice.status, docstatus: invoice.docstatus, grand_total: invoice.grand_total, total_advance: invoice.total_advance, outstanding_amount: invoice.outstanding_amount } : null
    }
  }

  async getPaymentModes(): Promise<PaymentMode[]> {
    return [{ name: 'Carte de crédit', has_account: true }, { name: 'Virement', has_account: true }, { name: 'Espèces', has_account: false }]
  }

  async recordAdvancePayment(input: RecordAdvanceInput): Promise<RecordAdvanceResult> {
    await LatencySimulator.inject('mutation')
    return { payment_entry: `DEMO-PE-${Date.now()}`, amount: input.amount, submitted: true }
  }

  async createFinalInvoice(rentalId: string): Promise<{ sales_invoice: string }> {
    await LatencySimulator.inject('mutation')
    return { sales_invoice: demoInvoices.find(row => row.cortex_rental_transaction === rentalId)?.name ?? `DEMO-SINV-${Date.now()}` }
  }

  // 13. Operations & rental lifecycle (DEMO data, explicit mock mode only)
  async listRentalSummaries(input: ListRentalSummariesInput): Promise<PagedResult<RentalSummary>> {
    await LatencySimulator.inject('fast')
    const needle = (input.search ?? '').toLowerCase()
    const rows = this.store.rentals
      .filter(r => (!input.state || r.rental_state === input.state) && (!needle || [r.id, r.customer_name, r.project_name ?? ''].some(v => v.toLowerCase().includes(needle))))
      .map(r => ({
        name: r.id, customer: r.customer_id, customer_name: r.customer_name, project_name: r.project_name ?? '', rental_state: r.rental_state,
        starts_at: r.starts_at, ends_at: r.ends_at, billable_days: r.billable_days, grand_total: r.grand_total, currency: r.currency ?? 'CAD', ready: r.readiness.overall_ready
      }))
    return this.pageOf(rows, input.page, input.page_size)
  }

  async getOperationsOverview(day?: string): Promise<OperationsOverview> {
    await LatencySimulator.inject('fast')
    const toRow = (r: RentalTransaction) => ({
      name: r.id, customer: r.customer_id, customer_name: r.customer_name, project_name: r.project_name ?? '', rental_state: r.rental_state,
      starts_at: r.starts_at, ends_at: r.ends_at,
      missing_requirements: (['customer_account_ready', 'insurance_ready', 'payment_ready'] as const).filter(k => !r.readiness[k])
    })
    const departures = this.store.rentals.filter(r => ['Reservation', 'Contract'].includes(r.rental_state)).map(toRow)
    const returns = this.store.rentals.filter(r => r.rental_state === 'Checked Out').map(toRow)
    return {
      provenance: 'mock', day: day ?? new Date().toISOString().slice(0, 10), generated_at: new Date().toISOString(),
      kpis: { departures: departures.length, returns: returns.length, overdue: 1, exceptions: 1, approvals_pending: this.store.approvals.filter(a => a.status === 'pending').length, inbound_pending: 2 },
      departures, returns, overdue: returns.slice(0, 1), exceptions: [],
      at_risk: departures.filter(r => r.missing_requirements.length),
      serials_out_of_service: [{ serial_no: 'DEMO-SN-ALX-004', item_code: 'DEMO-ITM-ALX35', status: 'Quarantine' }]
    }
  }

  private demoRentalUpdate(rentalId: string, update: (r: RentalTransaction) => void): GetRentalResponse {
    const rental = this.store.rentals.find(r => r.id === rentalId)
    if (!rental) throw new Error(`Location ${rentalId} introuvable.`)
    update(rental)
    rental.readiness.overall_ready = rental.readiness.customer_account_ready && rental.readiness.insurance_ready && rental.readiness.payment_ready
    rental.available_actions = demoActions(rental.rental_state, rental.final_invoice)
    return structuredClone(rental)
  }

  async setReadiness(rentalId: string, field: ReadinessField, value: boolean): Promise<GetRentalResponse> {
    await LatencySimulator.inject('mutation')
    return this.demoRentalUpdate(rentalId, r => { r.readiness[field] = value })
  }

  async cancelRental(rentalId: string): Promise<GetRentalResponse> {
    await LatencySimulator.inject('mutation')
    return this.demoRentalUpdate(rentalId, r => { r.rental_state = 'Cancelled' })
  }

  async closeRental(rentalId: string): Promise<GetRentalResponse> {
    await LatencySimulator.inject('mutation')
    return this.demoRentalUpdate(rentalId, r => { r.rental_state = 'Closed' })
  }

  async uploadRentalEvidence(rentalId: string, file: File): Promise<{ file_name: string; file_url: string }> {
    await LatencySimulator.inject('mutation')
    return { file_name: `DEMO-FILE-${rentalId}-${file.name}`, file_url: '' }
  }

  // 16. Consignment workflow & customers (DEMO, explicit mock mode only)
  async getOwner(ownerId: string): Promise<ConsignmentOwnerRecord> {
    await LatencySimulator.inject('fast')
    const owner = this.store.owners.find(o => o.id === ownerId)
    if (!owner) throw new Error(`Propriétaire introuvable : ${ownerId}`)
    return {
      ...this.demoOwnerRow(owner), billing_address: '',
      serials: this.store.serials.filter(s => s.owner_id === ownerId).map(s => ({ serial_no: s.serial_number, item_code: s.item_code, status: s.status })),
      statements: this.store.consignmentDashboard.pending_statements.filter(p => p.owner_id === ownerId).map(p => ({ period: p.period, status: p.status, amount: p.amount_due })),
      can_manage: true
    }
  }

  async saveOwner(owner: OwnerDraft): Promise<ConsignmentOwnerRecord> {
    await LatencySimulator.inject('mutation')
    const existing = owner.id ? this.store.owners.find(o => o.id === owner.id) : undefined
    if (existing) {
      Object.assign(existing, { display_name: owner.display_name ?? existing.display_name, default_commission_percentage: owner.default_commission_percentage ?? existing.default_commission_percentage, contact_email: owner.contact_email ?? existing.contact_email })
      return this.getOwner(existing.id)
    }
    const id = `DEMO-OWN-${String(this.store.owners.length + 1).padStart(3, '0')}`
    this.store.owners.push({ provenance: 'demo', last_synced_at: new Date().toISOString(), id, owner_code: owner.owner_code ?? id, display_name: owner.display_name ?? id, contact_email: owner.contact_email ?? '', default_commission_percentage: owner.default_commission_percentage ?? 70, active_serials_count: 0, pending_payout_amount: 0, currency: 'CAD' })
    return this.getOwner(id)
  }

  async setSerialOwner(serialNo: string, ownerId: string | null): Promise<void> {
    await LatencySimulator.inject('mutation')
    const serial = this.store.serials.find(s => s.serial_number === serialNo)
    if (serial) { serial.owner_id = ownerId ?? undefined; serial.is_consigned = Boolean(ownerId) }
  }

  private setDemoStatement(ownerId: string, period: string, status: 'draft' | 'approved' | 'paid') {
    const list = this.store.consignmentDashboard.pending_statements
    const existing = list.find(p => p.owner_id === ownerId && p.period === period)
    if (existing) existing.status = status
    else {
      const owner = this.store.owners.find(o => o.id === ownerId)
      list.push({ owner_id: ownerId, owner_name: owner?.display_name ?? ownerId, period, amount_due: owner?.pending_payout_amount ?? 0, status })
    }
  }

  async prepareStatement(ownerId: string, period: string): Promise<void> {
    await LatencySimulator.inject('mutation')
    this.setDemoStatement(ownerId, period, 'draft')
  }

  async approveStatement(ownerId: string, period: string): Promise<void> {
    await LatencySimulator.inject('mutation')
    this.setDemoStatement(ownerId, period, 'approved')
  }

  async markStatementPaid(ownerId: string, period: string): Promise<void> {
    await LatencySimulator.inject('mutation')
    this.setDemoStatement(ownerId, period, 'paid')
  }

  private demoCustomerRecord(customerId: string): CustomerRecord {
    const c = this.store.customers.find(x => x.id === customerId)
    if (!c) throw new Error(`Client introuvable : ${customerId}`)
    const rentals = this.store.rentals.filter(r => r.customer_id === c.id)
    const status = !c.insurance_valid_until ? 'unknown' : c.insurance_valid_until >= new Date().toISOString().slice(0, 10) ? 'valid' : 'expired'
    return {
      provenance: 'mock', name: c.id, customer_name: c.name, customer_type: 'Company', customer_group: 'Commercial', email: c.contact_email, phone: c.phone,
      insurance: { valid_until: c.insurance_valid_until || null, status }, currency: 'CAD',
      stats: { rentals: rentals.length, active_rentals: rentals.filter(r => ['Reservation', 'Contract', 'Checked Out'].includes(r.rental_state)).length, lifetime_value: rentals.filter(r => ['Returned', 'Closed'].includes(r.rental_state)).reduce((sum, r) => sum + r.grand_total, 0), outstanding: 0, disputes: 0 },
      rentals: rentals.map(r => ({ name: r.id, project_name: r.project_name ?? '', rental_state: r.rental_state, starts_at: r.starts_at, ends_at: r.ends_at, grand_total: r.grand_total })),
      invoices: [], payments: [], can_verify: true
    }
  }

  async listCustomers(input: ListCustomersInput): Promise<ListCustomersResponse> {
    await LatencySimulator.inject('fast')
    const q = (input.search ?? '').toLowerCase()
    const rows = this.store.customers.filter(c => !q || c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q)).map(c => {
      const record = this.demoCustomerRecord(c.id)
      return { name: c.id, customer_name: c.name, customer_group: 'Commercial', email: c.contact_email, phone: c.phone, rentals: record.stats.rentals, active_rentals: record.stats.active_rentals, outstanding: 0, insurance_status: record.insurance.status, insurance_valid_until: record.insurance.valid_until }
    })
    return { provenance: 'mock', items: rows.slice((input.page - 1) * input.page_size, input.page * input.page_size), total_count: rows.length, page: input.page, page_size: input.page_size, currency: 'CAD' }
  }

  async getCustomer(customer: string): Promise<CustomerRecord> {
    await LatencySimulator.inject('fast')
    return this.demoCustomerRecord(customer)
  }

  async createCustomer(input: NewCustomerInput): Promise<CustomerRecord> {
    await LatencySimulator.inject('mutation')
    const id = `DEMO-CUST-${String(this.store.customers.length + 1).padStart(3, '0')}`
    this.store.customers.push({ id, name: input.customer_name, contact_email: input.email ?? '', phone: input.phone ?? '', is_verified: false, insurance_valid_until: '', insurance_coverage_cad: 0, deposit_on_file_cad: 0, account_status: 'Review_Needed' })
    return this.demoCustomerRecord(id)
  }

  async setCustomerInsurance(customer: string, validUntil: string | null): Promise<CustomerRecord> {
    await LatencySimulator.inject('mutation')
    const c = this.store.customers.find(x => x.id === customer)
    if (c) c.insurance_valid_until = validUntil ?? ''
    return this.demoCustomerRecord(customer)
  }
}
