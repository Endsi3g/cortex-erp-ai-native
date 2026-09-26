import type { CortexApiClient } from '../CortexApiClient'
import type {
  AvailabilityMatrixInput,
  AvailabilityMatrixResponse,
  AvailabilityBlock,
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
  CreateUploadIntentInput,
  UploadIntentResponse,
  RegisterEvidenceInput,
  MutationResponse
} from '../contracts'
import type { Policies, PricingRuleInput, CompanySettingsInput, Team, AuditQuery, AuditPage, AuditEventDetail, ImportBatches, ImportBatch, ImportType, ImportAnalysis, ImportValidation, ImportRollback } from '../contracts/administration'
import type { InboxKind, InboxList, InboxDetail, AgentActivity, AgentActivityInput, AssistantStatus, ChatSessionSummary, ChatSessionDetail, SendChatInput, SendChatResult, ActionDecision } from '../contracts/ai'
import type { RentalSummary, ListRentalSummariesInput, ReadinessField, OperationsOverview } from '../contracts'
import type { InvoiceRow, PaymentRow, PagedResult, ListInvoicesInput, ListPaymentsInput, RentalBilling, PaymentMode, RecordAdvanceInput, RecordAdvanceResult } from '../contracts'
import type { PnlFilterOptions, PnlFilters, PnlReport, GlobalSearchResponse } from '../contracts'
import { HttpClient } from './httpClient'
import { generateIdempotencyKey } from '@/utils/idempotency'

export class HttpCortexApiClient implements CortexApiClient {
  private http: HttpClient

  constructor(http?: HttpClient) {
    this.http = http || new HttpClient()
  }

  // 1. Availability
  async getAvailabilityMatrix(input: AvailabilityMatrixInput): Promise<AvailabilityMatrixResponse> {
    const response = await this.http.get<FrappeResult<{
      starts_at: string
      ends_at: string
      items: Array<{
        item_code: string
        item_name: string
        category?: string | null
        is_serialized: boolean
        fleet_quantity: number
        has_conflict: boolean
        blocks: Array<{
          transaction: string
          rental_state: AvailabilityBlock['state']
          customer: string
          starts_at: string
          ends_at: string
          qty: number
        }>
      }>
    }>>('/cortex_rental.api.v1.availability.get_matrix', {
      starts_at: `${input.start_date} 00:00:00`,
      ends_at: `${input.end_date} 23:59:59`,
      category: input.category,
      search: input.search
    })
    const data = unwrapFrappe(response)

    return {
      provenance: 'api',
      last_synced_at: new Date().toISOString(),
      start_date: data.starts_at,
      end_date: data.ends_at,
      rows: data.items.map(item => ({
        item_code: item.item_code,
        item_name: item.item_name,
        category: item.category || 'Uncategorized',
        total_fleet: item.fleet_quantity,
        is_serialized: item.is_serialized,
        blocks: item.blocks.map(block => ({
          id: `${block.transaction}:${item.item_code}`,
          rental_id: block.transaction,
          rental_name: block.transaction,
          customer_name: block.customer,
          state: block.rental_state,
          start_date: block.starts_at,
          end_date: block.ends_at,
          is_conflict: item.has_conflict,
          ...(item.has_conflict ? { conflict_reason: 'Le service ERPNext signale un conflit de capacité sur cette ligne; vérifie les périodes exactes.' } : {})
        }))
      }))
    }
  }

  async checkInventoryAvailability(input: AvailabilityCheckInput): Promise<AvailabilityCheckResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<AvailabilityCheckResponse>>(
      '/cortex_rental.api.v1.availability.check_for_staff', input
    ))
  }

  async getAvailabilityAlternatives(input: AlternativesInput): Promise<AlternativesResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<AlternativesResponse>>(
      '/cortex_rental.api.v1.availability.get_alternatives', input
    ))
  }

  // 2. Rentals
  async listRentals(input: ListRentalsInput): Promise<ListRentalsResponse> {
    const response = await this.http.get<FrappeResult<ListRentalsResponse>>('/cortex_rental.api.v1.rentals.list_rentals', input)
    return unwrapFrappe(response)
  }

  async getRental(input: GetRentalInput): Promise<GetRentalResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GetRentalResponse>>('/cortex_rental.api.v1.rentals.get_rental', { name: input.id }))
  }

  async searchRentalCustomers(query: string): Promise<RentalCustomerOption[]> {
    const result = unwrapFrappe(await this.http.get<FrappeResult<{ items: RentalCustomerOption[] }>>(
      '/cortex_rental.api.v1.rentals.search_rental_customers', { query }
    ))
    return result.items
  }

  async searchRentalCatalog(query: string): Promise<RentalCatalogOption[]> {
    const result = unwrapFrappe(await this.http.get<FrappeResult<{ items: RentalCatalogOption[] }>>(
      '/cortex_rental.api.v1.rentals.search_rental_catalog', { query }
    ))
    return result.items
  }

  async previewPricing(input: PreviewPricingInput): Promise<PreviewPricingResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<PreviewPricingResponse>>('/cortex_rental.api.v1.rentals.preview_pricing', input))
  }

  async createQuoteDraft(input: CreateQuoteDraftInput): Promise<MutationResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.rentals.create_quote_draft', input, makeIdempotencyKey()))
  }

  async updateQuoteDraft(input: UpdateQuoteDraftInput): Promise<MutationResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.rentals.update_quote_draft', input, makeIdempotencyKey()))
  }

  async requestReservation(input: RequestReservationInput): Promise<MutationResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.rentals.request_reservation', {
      name: input.rental_id, version: input.version
    }, makeIdempotencyKey()))
  }

  async requestContractApproval(input: RequestContractApprovalInput): Promise<MutationResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.rentals.request_contract', {
      name: input.rental_id, version: input.version, override_reason: input.override_reason
    }, makeIdempotencyKey()))
  }

  async getRentalAudit(input: GetRentalAuditInput): Promise<GetRentalAuditResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GetRentalAuditResponse>>('/cortex_rental.api.v1.rentals.get_rental_audit', {
      rental_id: input.rental_id
    }))
  }

  // 3. Warehouse
  async startCheckout(input: StartCheckoutInput): Promise<MutationResponse> {
    const rental = await this.getRental({ id: input.rental_id })
    if (rental.rental_state !== 'Contract') throw new Error('Un check-out exige un contrat approuvé.')
    return { request_id: `checkout:${rental.id}`, entity_id: rental.id, status: 'completed', approval_required: false, mutation_performed: false }
  }

  async scanCheckoutSerial(input: ScanCheckoutSerialInput): Promise<MutationResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.checkout.record_checkout_scan', input, makeIdempotencyKey()))
  }

  async completeCheckout(input: CompleteCheckoutInput): Promise<MutationResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.checkout.complete_checkout', input, makeIdempotencyKey()))
  }

  async startCheckin(input: StartCheckinInput): Promise<MutationResponse> {
    const rental = await this.getRental({ id: input.rental_id })
    if (rental.rental_state !== 'Checked Out') throw new Error('Un check-in exige une location actuellement sortie.')
    return { request_id: `checkin:${rental.id}`, entity_id: rental.id, status: 'completed', approval_required: false, mutation_performed: false }
  }

  async scanCheckinSerial(input: ScanCheckinSerialInput): Promise<MutationResponse> {
    const result = unwrapFrappe(await this.http.get<FrappeResult<Record<string, unknown>>>('/cortex_rental.api.v1.checkin.lookup_scan', { scan_code: input.serial_number }))
    const transaction = result.transaction as Record<string, unknown> | undefined
    if (result.type !== 'serial' || result.serial_no !== input.serial_number || transaction?.name !== input.rental_id) {
      throw new Error('Ce numéro de série n’est pas affecté à cette location sortie.')
    }
    return { request_id: `scan:${input.rental_id}:${input.serial_number}`, entity_id: input.rental_id, status: 'completed', approval_required: false, mutation_performed: false }
  }

  async markSerialMissing(input: MarkSerialMissingInput): Promise<MutationResponse> {
    const result = unwrapFrappe(await this.http.get<FrappeResult<Record<string, unknown>>>('/cortex_rental.api.v1.checkin.lookup_scan', { scan_code: input.serial_number }))
    if (result.type !== 'serial' || (result.transaction as Record<string, unknown> | undefined)?.name !== input.rental_id) throw new Error('Ce numéro de série n’appartient pas à cette location sortie.')
    return { request_id: `missing:${input.rental_id}:${input.serial_number}`, entity_id: input.rental_id, status: 'completed', approval_required: false, mutation_performed: false }
  }

  async addDamageEvidence(input: AddDamageEvidenceInput): Promise<MutationResponse> {
    void input
    throw new Error('Les dommages sont enregistrés avec les articles et preuves lors de la validation finale du check-in.')
  }

  async completePartialReturn(input: CompletePartialReturnInput): Promise<MutationResponse> {
    // submit_checkin answers with the completed Cortex Check-In, not a mutation envelope.
    const checkin = unwrapFrappe(await this.http.post<FrappeResult<{ id: string; status: string; transaction_fully_returned?: boolean }>>('/cortex_rental.api.v1.checkin.submit_checkin', {
      transaction_id: input.rental_id,
      items: input.items || [],
      notes: input.notes || '',
      finalize_mode: input.finalize_mode || 'auto'
    }, makeIdempotencyKey()))
    return {
      request_id: checkin.id,
      entity_id: input.rental_id,
      status: checkin.status === 'Completed' ? 'completed' : 'failed',
      approval_required: false,
      mutation_performed: checkin.status === 'Completed'
    }
  }

  async lookupScan(input: LookupScanInput): Promise<LookupScanResponse> {
    const result = unwrapFrappe(await this.http.get<FrappeResult<Record<string, unknown>>>('/cortex_rental.api.v1.checkin.lookup_scan', { scan_code: input.barcode }))
    const transaction = result.transaction as Record<string, unknown> | undefined
    const type = result.type === 'serial' ? 'serial_number' : result.type === 'transaction' ? 'rental' : result.type === 'item' ? 'item' : 'unknown'
    return { provenance: 'api', last_synced_at: new Date().toISOString(), barcode: input.barcode,
      entity_type: type, entity_id: String(result.serial_no || transaction?.name || result.item_code || ''),
      display_title: String(result.item_name || transaction?.customer_name || result.scan_code || input.barcode),
      current_status: String(transaction ? 'Checked Out' : result.type || 'unknown'),
      ...(transaction?.name ? { associated_rental_id: String(transaction.name) } : {}) }
  }

  // 4. Consignment
  async listOwners(input: ListOwnersInput): Promise<ListOwnersResponse> {
    const dashboard = await this.getConsignmentDashboard({ period: input.period })
    const needle = (input.search ?? '').toLowerCase()
    const items = dashboard.owners.filter(owner => !needle || [owner.display_name, owner.owner_code].some(value => value.toLowerCase().includes(needle)))
    return { provenance: 'api', items, total_count: items.length }
  }

  async getConsignmentDashboard(input: ConsignmentDashboardInput): Promise<ConsignmentDashboardResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ConsignmentDashboardResponse>>('/cortex_rental.api.v1.consignment.get_dashboard', { period: input.period }))
  }

  async getOwnerStatement(input: OwnerStatementInput): Promise<OwnerStatementResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<OwnerStatementResponse>>('/cortex_rental.api.v1.consignment.get_owner_statement', { owner: input.owner_id, period: input.period }))
  }

  // 5. Approvals
  async listApprovalRequests(input: ListApprovalRequestsInput): Promise<ListApprovalsResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListApprovalsResponse>>('/cortex_rental.api.v1.approval_queue.list_approval_requests', input))
  }

  async getApprovalRequest(input: GetApprovalRequestInput): Promise<GetApprovalResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GetApprovalResponse>>('/cortex_rental.api.v1.approval_queue.get_approval_request', { name: input.id }))
  }

  async approveApprovalRequest(input: ApproveApprovalInput): Promise<MutationResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.approval_queue.decide_approval', {
      name: input.id, decision: 'approve', reason: input.notes
    }, makeIdempotencyKey()))
  }

  async rejectApprovalRequest(input: RejectApprovalInput): Promise<MutationResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.approval_queue.decide_approval', {
      name: input.id, decision: 'reject', reason: input.reason
    }, makeIdempotencyKey()))
  }

  // 6. AI
  async listInbox(kind?: InboxKind, includeClosed = false): Promise<InboxList> {
    return unwrapFrappe(await this.http.get<FrappeResult<InboxList>>('/cortex_rental.api.v1.ai.list_inbox', { kind, include_closed: includeClosed ? '1' : '0' }))
  }

  async getInboxItem(kind: InboxKind, sourceId: string): Promise<InboxDetail> {
    return unwrapFrappe(await this.http.get<FrappeResult<InboxDetail>>('/cortex_rental.api.v1.ai.get_inbox_item', { kind, source_id: sourceId }))
  }

  async rejectInbound(sourceId: string, reason: string): Promise<void> {
    await this.http.post('/cortex_rental.api.v1.ai.reject_inbound', { source_id: sourceId, reason }, makeIdempotencyKey())
  }

  async linkInboundToRental(sourceId: string, rentalId: string): Promise<void> {
    await this.http.post('/cortex_rental.api.v1.ai.link_inbound_to_rental', { source_id: sourceId, rental: rentalId }, makeIdempotencyKey())
  }

  async listAgentActivity(input: AgentActivityInput): Promise<AgentActivity> {
    return unwrapFrappe(await this.http.get<FrappeResult<AgentActivity>>('/cortex_rental.api.v1.ai.list_agent_activity', { ...input }))
  }

  // 7. Assistant
  async getAssistantStatus(): Promise<AssistantStatus> {
    return unwrapFrappe(await this.http.get<FrappeResult<AssistantStatus>>('/cortex_rental.api.v1.chat.get_assistant_status'))
  }

  async sendChatMessage(input: SendChatInput): Promise<SendChatResult> {
    return unwrapFrappe(await this.http.post<FrappeResult<SendChatResult>>('/cortex_rental.api.v1.chat.send_message', {
      chat_session_id: input.chat_session_id,
      message: input.message,
      context: JSON.stringify(input.context),
      client_turn_id: input.client_turn_id
    }))
  }

  async getChatSession(sessionId: string): Promise<ChatSessionDetail> {
    return unwrapFrappe(await this.http.get<FrappeResult<ChatSessionDetail>>('/cortex_rental.api.v1.chat.get_session', { name: sessionId }))
  }

  async decideAiAction(actionId: string, decision: 'confirm' | 'cancel'): Promise<ActionDecision> {
    return unwrapFrappe(await this.http.post<FrappeResult<ActionDecision>>('/cortex_rental.api.v1.chat.decide_action', { action_id: actionId, decision }))
  }

  async listChatSessions(): Promise<ChatSessionSummary[]> {
    return unwrapFrappe(await this.http.get<FrappeResult<ChatSessionSummary[]>>('/cortex_rental.api.v1.chat.list_sessions'))
  }

  // 8. Catalog, Fleet, Policies, Audit & Migration
  async listEquipment(input: ListEquipmentInput): Promise<ListEquipmentResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListEquipmentResponse>>('/cortex_rental.api.v1.catalog.list_equipment', { ...input }))
  }

  async getEquipment(input: GetEquipmentInput): Promise<GetEquipmentResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GetEquipmentResponse>>('/cortex_rental.api.v1.catalog.get_equipment', { item_code: input.item_code }))
  }

  async getSerial(input: GetSerialInput): Promise<GetSerialResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GetSerialResponse>>('/cortex_rental.api.v1.catalog.get_serial', { serial_no: input.serial_number }))
  }

  async listKits(input: ListKitsInput): Promise<ListKitsResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListKitsResponse>>('/cortex_rental.api.v1.catalog.list_kits', { include_inactive: input.include_inactive ? 1 : 0 }))
  }

  async updateEquipmentProfile(itemCode: string, changes: EquipmentProfileChanges): Promise<GetEquipmentResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<GetEquipmentResponse>>('/cortex_rental.api.v1.catalog.update_equipment_profile', { item_code: itemCode, changes: JSON.stringify(changes) }))
  }

  async setSerialStatus(serialNo: string, status: SerialStatus, reason: string): Promise<GetSerialResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<GetSerialResponse>>('/cortex_rental.api.v1.catalog.set_serial_status', { serial_no: serialNo, status, reason }))
  }

  async saveKit(kit: RentalKit): Promise<RentalKit> {
    return unwrapFrappe(await this.http.post<FrappeResult<RentalKit>>('/cortex_rental.api.v1.catalog.save_kit', { kit: JSON.stringify(kit) }))
  }

  // 9. Upload & Evidence
  async createUploadIntent(input: CreateUploadIntentInput): Promise<UploadIntentResponse> {
    return this.http.post<UploadIntentResponse>('/upload/intent', input)
  }

  async registerEvidence(input: RegisterEvidenceInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>('/upload/register_evidence', input)
  }

  // 10. Finance
  async getPnlFilterOptions(): Promise<PnlFilterOptions> {
    return unwrapFrappe(await this.http.get<FrappeResult<PnlFilterOptions>>(
      '/cortex_rental.api.v1.accounting.get_pnl_filter_options'
    ))
  }

  async getProfitAndLoss(filters: PnlFilters): Promise<PnlReport> {
    const { dimensions, accumulated_values, include_default_book_entries, filter_based_on, ...rest } = filters
    const params: Record<string, string | undefined> = {
      ...Object.fromEntries(Object.entries(rest).map(([key, value]) => [key, value === '' ? undefined : value as string | undefined])),
      accumulated_values: accumulated_values ? '1' : '0',
      include_default_book_entries: include_default_book_entries ? '1' : '0',
      ...(dimensions ?? {})
    }
    if (filter_based_on === 'Fiscal Year') {
      delete params.from_date
      delete params.to_date
    } else {
      delete params.from_fiscal_year
      delete params.to_fiscal_year
    }
    return unwrapFrappe(await this.http.get<FrappeResult<PnlReport>>(
      '/cortex_rental.api.v1.accounting.get_profit_and_loss', params
    ))
  }

  // 12. Billing
  async listInvoices(input: ListInvoicesInput): Promise<PagedResult<InvoiceRow>> {
    return unwrapFrappe(await this.http.get<FrappeResult<PagedResult<InvoiceRow>>>('/cortex_rental.api.v1.billing.list_invoices', { ...input }))
  }

  async listPayments(input: ListPaymentsInput): Promise<PagedResult<PaymentRow>> {
    return unwrapFrappe(await this.http.get<FrappeResult<PagedResult<PaymentRow>>>('/cortex_rental.api.v1.billing.list_payments', { ...input }))
  }

  async getRentalBilling(rentalId: string): Promise<RentalBilling> {
    return unwrapFrappe(await this.http.get<FrappeResult<RentalBilling>>('/cortex_rental.api.v1.billing.get_rental_billing', { rental_id: rentalId }))
  }

  async getPaymentModes(): Promise<PaymentMode[]> {
    return unwrapFrappe(await this.http.get<FrappeResult<PaymentMode[]>>('/cortex_rental.api.v1.billing.get_payment_modes'))
  }

  async recordAdvancePayment(input: RecordAdvanceInput): Promise<RecordAdvanceResult> {
    return unwrapFrappe(await this.http.post<FrappeResult<RecordAdvanceResult>>('/cortex_rental.api.v1.billing.record_advance_payment', input, makeIdempotencyKey()))
  }

  async createFinalInvoice(rentalId: string): Promise<{ sales_invoice: string }> {
    return unwrapFrappe(await this.http.post<FrappeResult<{ sales_invoice: string }>>('/cortex_rental.api.v1.billing.create_final_invoice', { rental_id: rentalId }, makeIdempotencyKey()))
  }

  // 13. Operations & rental lifecycle
  async listRentalSummaries(input: ListRentalSummariesInput): Promise<PagedResult<RentalSummary>> {
    return unwrapFrappe(await this.http.get<FrappeResult<PagedResult<RentalSummary>>>('/cortex_rental.api.v1.rentals.list_rental_summaries', { ...input }))
  }

  async getOperationsOverview(day?: string): Promise<OperationsOverview> {
    return unwrapFrappe(await this.http.get<FrappeResult<OperationsOverview>>('/cortex_rental.api.v1.operations.get_operations_overview', { day }))
  }

  async setReadiness(rentalId: string, field: ReadinessField, value: boolean, note?: string): Promise<GetRentalResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<GetRentalResponse>>('/cortex_rental.api.v1.rentals.set_readiness', { name: rentalId, field, value: value ? 1 : 0, note }))
  }

  async cancelRental(rentalId: string, reason: string): Promise<GetRentalResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<GetRentalResponse>>('/cortex_rental.api.v1.rentals.cancel_rental', { name: rentalId, reason }, makeIdempotencyKey()))
  }

  async closeRental(rentalId: string): Promise<GetRentalResponse> {
    return unwrapFrappe(await this.http.post<FrappeResult<GetRentalResponse>>('/cortex_rental.api.v1.rentals.close_rental', { name: rentalId }, makeIdempotencyKey()))
  }

  // 14. Evidence files
  async uploadRentalEvidence(rentalId: string, file: File): Promise<{ file_name: string; file_url: string }> {
    const form = new FormData()
    form.append('file', file, file.name)
    form.append('is_private', '1')
    form.append('doctype', 'Cortex Rental Transaction')
    form.append('docname', rentalId)
    form.append('folder', 'Home/Attachments')
    const result = unwrapFrappe(await this.http.upload<FrappeResult<{ name: string; file_url: string }>>('/upload_file', form))
    return { file_name: result.name, file_url: result.file_url }
  }

  // 16. Consignment workflow & customers
  async getOwner(ownerId: string, period?: string): Promise<ConsignmentOwnerRecord> {
    return unwrapFrappe(await this.http.get<FrappeResult<ConsignmentOwnerRecord>>('/cortex_rental.api.v1.consignment.get_owner', { owner: ownerId, period }))
  }

  async saveOwner(owner: OwnerDraft): Promise<ConsignmentOwnerRecord> {
    return unwrapFrappe(await this.http.post<FrappeResult<ConsignmentOwnerRecord>>('/cortex_rental.api.v1.consignment.save_owner', { owner: JSON.stringify(owner) }))
  }

  async setSerialOwner(serialNo: string, ownerId: string | null): Promise<void> {
    await this.http.post('/cortex_rental.api.v1.consignment.set_serial_owner', { serial_no: serialNo, owner: ownerId })
  }

  async prepareStatement(ownerId: string, period: string): Promise<void> {
    await this.http.post('/cortex_rental.api.v1.consignment.prepare_statement', { owner: ownerId, period }, makeIdempotencyKey())
  }

  async approveStatement(ownerId: string, period: string): Promise<void> {
    await this.http.post('/cortex_rental.api.v1.consignment.approve_statement', { owner: ownerId, period })
  }

  async markStatementPaid(ownerId: string, period: string, reference: string): Promise<void> {
    await this.http.post('/cortex_rental.api.v1.consignment.mark_statement_paid', { owner: ownerId, period, reference })
  }

  async listCustomers(input: ListCustomersInput): Promise<ListCustomersResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListCustomersResponse>>('/cortex_rental.api.v1.clients.list_customers', { ...input }))
  }

  async getCustomer(customer: string): Promise<CustomerRecord> {
    return unwrapFrappe(await this.http.get<FrappeResult<CustomerRecord>>('/cortex_rental.api.v1.clients.get_customer', { customer }))
  }

  async createCustomer(input: NewCustomerInput): Promise<CustomerRecord> {
    return unwrapFrappe(await this.http.post<FrappeResult<CustomerRecord>>('/cortex_rental.api.v1.clients.create_customer', input, makeIdempotencyKey()))
  }

  async setCustomerInsurance(customer: string, validUntil: string | null, note?: string): Promise<CustomerRecord> {
    return unwrapFrappe(await this.http.post<FrappeResult<CustomerRecord>>('/cortex_rental.api.v1.clients.set_insurance', { customer, valid_until: validUntil, note }))
  }

  // 11. Global search
  async globalSearch(query: string): Promise<GlobalSearchResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GlobalSearchResponse>>(
      '/cortex_rental.api.v1.search.global_search', { query }
    ))
  }

  // 17. Administration
  async getPolicies(): Promise<Policies> {
    return unwrapFrappe(await this.http.get<FrappeResult<Policies>>('/cortex_rental.api.v1.admin.get_policies'))
  }

  async savePricingRule(input: PricingRuleInput): Promise<Policies> {
    return unwrapFrappe(await this.http.post<FrappeResult<Policies>>('/cortex_rental.api.v1.admin.save_pricing_rule', { ...input, is_active: input.is_active ? 1 : 0 }))
  }

  async saveCompanySettings(values: CompanySettingsInput): Promise<Policies> {
    return unwrapFrappe(await this.http.post<FrappeResult<Policies>>('/cortex_rental.api.v1.admin.save_company_settings', { values: JSON.stringify(values) }))
  }

  async listTeam(): Promise<Team> {
    return unwrapFrappe(await this.http.get<FrappeResult<Team>>('/cortex_rental.api.v1.admin.list_team'))
  }

  async setUserRoles(user: string, roles: string[]): Promise<Team> {
    return unwrapFrappe(await this.http.post<FrappeResult<Team>>('/cortex_rental.api.v1.admin.set_user_roles', { user, roles: JSON.stringify(roles) }))
  }

  async listAuditEvents(query: AuditQuery): Promise<AuditPage> {
    return unwrapFrappe(await this.http.get<FrappeResult<AuditPage>>('/cortex_rental.api.v1.admin.list_audit_events', { ...query }))
  }

  async getAuditEvent(name: string): Promise<AuditEventDetail> {
    return unwrapFrappe(await this.http.get<FrappeResult<AuditEventDetail>>('/cortex_rental.api.v1.admin.get_audit_event', { name }))
  }

  async listImportBatches(): Promise<ImportBatches> {
    return unwrapFrappe(await this.http.get<FrappeResult<ImportBatches>>('/cortex_rental.api.v1.imports.list_import_batches'))
  }

  async getImportBatch(name: string): Promise<ImportBatch> {
    return unwrapFrappe(await this.http.get<FrappeResult<ImportBatch>>('/cortex_rental.api.v1.imports.get_import_batch', { batch: name }))
  }

  async createImportBatch(importType: ImportType): Promise<ImportBatch> {
    return unwrapFrappe(await this.http.post<FrappeResult<ImportBatch>>('/cortex_rental.api.v1.imports.create_import_batch', { import_type: importType }))
  }

  async uploadImportFile(batch: string, file: File): Promise<void> {
    const form = new FormData()
    form.append('file', file, file.name)
    form.append('is_private', '1')
    form.append('doctype', 'Cortex Import Batch')
    form.append('docname', batch)
    form.append('fieldname', 'source_file')
    await this.http.upload('/upload_file', form)
  }

  async analyzeImport(batch: string): Promise<ImportAnalysis> {
    return unwrapFrappe(await this.http.post<FrappeResult<ImportAnalysis>>('/cortex_rental.api.v1.imports.analyze_import', { batch }))
  }

  async validateImport(batch: string, mapping: Record<string, string | null>): Promise<ImportValidation> {
    return unwrapFrappe(await this.http.post<FrappeResult<ImportValidation>>('/cortex_rental.api.v1.imports.validate_import', { batch, mapping: JSON.stringify(mapping) }))
  }

  async runImport(batch: string): Promise<ImportBatch> {
    return unwrapFrappe(await this.http.post<FrappeResult<ImportBatch>>('/cortex_rental.api.v1.imports.run_import', { batch }, makeIdempotencyKey()))
  }

  async rollbackImport(batch: string, reason: string): Promise<ImportRollback> {
    return unwrapFrappe(await this.http.post<FrappeResult<ImportRollback>>('/cortex_rental.api.v1.imports.rollback_import', { batch, reason }, makeIdempotencyKey()))
  }
}

type FrappeResult<T> = T | { message: { data: T } | T }

function unwrapFrappe<T>(response: FrappeResult<T>): T {
  if (response && typeof response === 'object' && 'message' in response) {
    const message = response.message
    if (message && typeof message === 'object' && 'data' in message) return message.data as T
    return message as T
  }
  return response as T
}

function makeIdempotencyKey(): string {
  return generateIdempotencyKey()
}
