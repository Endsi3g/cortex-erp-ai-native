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
  OwnerStatementExportInput,
  ListApprovalRequestsInput,
  ListApprovalsResponse,
  GetApprovalRequestInput,
  GetApprovalResponse,
  ApproveApprovalInput,
  RejectApprovalInput,
  ListInboundRequestsInput,
  ListInboundRequestsResponse,
  GetInboundRequestInput,
  GetInboundRequestResponse,
  ListAiDraftsInput,
  ListAiDraftsResponse,
  GetAgentActivityInput,
  AgentActivityResponse,
  CreateCopilotSessionInput,
  CreateCopilotSessionResponse,
  SendCopilotMessageInput,
  SendCopilotMessageResponse,
  GetCopilotSessionInput,
  GetCopilotSessionResponse,
  ListCopilotSessionsInput,
  ListCopilotSessionsResponse,
  PinCopilotContextInput,
  ClearCopilotContextInput,
  ListEquipmentInput,
  ListEquipmentResponse,
  GetEquipmentInput,
  GetEquipmentResponse,
  GetSerialInput,
  GetSerialResponse,
  ListKitsInput,
  ListKitsResponse,
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
  MutationResponse,
  OperationsOverviewResponse,
  ListCustomersInput,
  ListCustomersResponse,
  ProfitAndLossInput,
  ProfitAndLossResponse
} from '../contracts'
import { HttpClient, CortexUnavailableError } from './httpClient'
import { generateIdempotencyKey } from '@/utils/idempotency'

export class HttpCortexApiClient implements CortexApiClient {
  private http: HttpClient

  constructor(http?: HttpClient) {
    this.http = http || new HttpClient()
  }

  // 0. Operations cockpit
  async getOperationsOverview(): Promise<OperationsOverviewResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<OperationsOverviewResponse>>('/cortex_rental.api.v1.operations.get_operations_overview'))
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
    return unwrapFrappe(await this.http.post<FrappeResult<MutationResponse>>('/cortex_rental.api.v1.checkin.submit_checkin', {
      transaction_id: input.rental_id,
      items: input.items || [],
      notes: input.notes || '',
      finalize_mode: input.finalize_mode || 'auto'
    }, makeIdempotencyKey()))
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

  // 3b. Customers & accounting
  async listCustomers(input: ListCustomersInput): Promise<ListCustomersResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListCustomersResponse>>('/cortex_rental.api.v1.customers.list_customers', input))
  }

  async getProfitAndLoss(input: ProfitAndLossInput): Promise<ProfitAndLossResponse> {
    const query: Record<string, string> = {}
    for (const [key, value] of Object.entries(input)) {
      if (value !== undefined && value !== '') query[key] = typeof value === 'boolean' ? (value ? '1' : '0') : String(value)
    }
    return unwrapFrappe(await this.http.get<FrappeResult<ProfitAndLossResponse>>('/cortex_rental.api.v1.accounting.get_profit_and_loss', query))
  }

  // 4. Consignment
  async listOwners(input: ListOwnersInput): Promise<ListOwnersResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListOwnersResponse>>('/cortex_rental.api.v1.consignment.list_owners', input))
  }

  async getConsignmentDashboard(input: ConsignmentDashboardInput): Promise<ConsignmentDashboardResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ConsignmentDashboardResponse>>('/cortex_rental.api.v1.consignment.get_consignment_dashboard', input))
  }

  async getOwnerStatement(input: OwnerStatementInput): Promise<OwnerStatementResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<OwnerStatementResponse>>('/cortex_rental.api.v1.consignment.get_owner_statement', input))
  }

  async requestOwnerStatementExport(_input: OwnerStatementExportInput): Promise<MutationResponse> {
    throw new CortexUnavailableError("L'export du relevé propriétaire (PDF/CSV) n'est pas encore disponible côté serveur.")
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

  // 6. Inbound & Telemetry
  async listInboundRequests(input: ListInboundRequestsInput): Promise<ListInboundRequestsResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListInboundRequestsResponse>>('/cortex_rental.api.v1.intelligence.list_inbound_requests', input))
  }

  async getInboundRequest(input: GetInboundRequestInput): Promise<GetInboundRequestResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GetInboundRequestResponse>>('/cortex_rental.api.v1.intelligence.get_inbound_request', { id: input.id }))
  }

  async listAiDrafts(input: ListAiDraftsInput): Promise<ListAiDraftsResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListAiDraftsResponse>>('/cortex_rental.api.v1.intelligence.list_ai_drafts', input))
  }

  async getAgentActivity(input: GetAgentActivityInput): Promise<AgentActivityResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<AgentActivityResponse>>('/cortex_rental.api.v1.intelligence.get_agent_activity', input))
  }

  // 7. Copilot — served by the Desk Assistant page, which talks to cortex_rental.api.v1.chat directly.
  async createCopilotSession(_input: CreateCopilotSessionInput): Promise<CreateCopilotSessionResponse> {
    throw new CortexUnavailableError("L'assistant Cortex se trouve dans la page Assistant du Desk (cortex_rental.api.v1.chat).")
  }

  async sendCopilotMessage(_input: SendCopilotMessageInput): Promise<SendCopilotMessageResponse> {
    throw new CortexUnavailableError("L'assistant Cortex se trouve dans la page Assistant du Desk (cortex_rental.api.v1.chat).")
  }

  async getCopilotSession(_input: GetCopilotSessionInput): Promise<GetCopilotSessionResponse> {
    throw new CortexUnavailableError("L'assistant Cortex se trouve dans la page Assistant du Desk (cortex_rental.api.v1.chat).")
  }

  async listCopilotSessions(_input: ListCopilotSessionsInput): Promise<ListCopilotSessionsResponse> {
    throw new CortexUnavailableError("L'assistant Cortex se trouve dans la page Assistant du Desk (cortex_rental.api.v1.chat).")
  }

  async pinCopilotContext(_input: PinCopilotContextInput): Promise<MutationResponse> {
    throw new CortexUnavailableError("L'assistant Cortex se trouve dans la page Assistant du Desk (cortex_rental.api.v1.chat).")
  }

  async clearCopilotContext(_input: ClearCopilotContextInput): Promise<MutationResponse> {
    throw new CortexUnavailableError("L'assistant Cortex se trouve dans la page Assistant du Desk (cortex_rental.api.v1.chat).")
  }

  // 8. Catalog, Fleet, Policies, Audit & Migration
  async listEquipment(input: ListEquipmentInput): Promise<ListEquipmentResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListEquipmentResponse>>('/cortex_rental.api.v1.catalog.list_equipment', input))
  }

  async getEquipment(input: GetEquipmentInput): Promise<GetEquipmentResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GetEquipmentResponse>>('/cortex_rental.api.v1.catalog.get_equipment', { item_code: input.item_code }))
  }

  async getSerial(input: GetSerialInput): Promise<GetSerialResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<GetSerialResponse>>('/cortex_rental.api.v1.catalog.get_serial', { serial_number: input.serial_number }))
  }

  async listKits(input: ListKitsInput): Promise<ListKitsResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListKitsResponse>>('/cortex_rental.api.v1.catalog.list_kits', input))
  }

  // Administration screens are the native ERPNext list views (Rental Pricing Rule, Role Permission
  // Manager, Data Import): the sidebar links there, so no Cortex read model exists for them.
  async listRentalPolicies(_input: ListRentalPoliciesInput): Promise<ListRentalPoliciesResponse> {
    throw new CortexUnavailableError('Les règles tarifaires se gèrent dans la liste native « Rental Pricing Rule ».')
  }

  async getTeamRoles(_input: GetTeamRolesInput): Promise<TeamRolesResponse> {
    throw new CortexUnavailableError('Les rôles et accès se gèrent dans le gestionnaire de permissions ERPNext.')
  }

  async listMigrationBatches(_input: ListMigrationBatchesInput): Promise<MigrationBatchesResponse> {
    throw new CortexUnavailableError("Les imports se gèrent dans « Data Import » d'ERPNext.")
  }

  async listAuditEvents(input: ListAuditEventsInput): Promise<ListAuditEventsResponse> {
    return unwrapFrappe(await this.http.get<FrappeResult<ListAuditEventsResponse>>('/cortex_rental.api.v1.intelligence.list_audit_events', input))
  }

  // 9. Upload & Evidence — private file upload is not exposed by a Cortex endpoint yet;
  // check-in damage evidence is submitted together with the check-in itself.
  async createUploadIntent(_input: CreateUploadIntentInput): Promise<UploadIntentResponse> {
    throw new CortexUnavailableError("Le téléversement de preuves n'est pas encore disponible côté serveur.")
  }

  async registerEvidence(_input: RegisterEvidenceInput): Promise<MutationResponse> {
    throw new CortexUnavailableError("L'enregistrement de preuves n'est pas encore disponible côté serveur.")
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
