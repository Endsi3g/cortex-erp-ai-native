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
  MutationResponse
} from '../contracts'
import { HttpClient } from './httpClient'

export class HttpCortexApiClient implements CortexApiClient {
  private http: HttpClient

  constructor(http?: HttpClient) {
    this.http = http || new HttpClient()
  }

  // 1. Availability
  async getAvailabilityMatrix(input: AvailabilityMatrixInput): Promise<AvailabilityMatrixResponse> {
    return this.http.get<AvailabilityMatrixResponse>('/availability/matrix', input)
  }

  async checkInventoryAvailability(input: AvailabilityCheckInput): Promise<AvailabilityCheckResponse> {
    return this.http.post<AvailabilityCheckResponse>('/availability/check', input)
  }

  async getAvailabilityAlternatives(input: AlternativesInput): Promise<AlternativesResponse> {
    return this.http.get<AlternativesResponse>('/availability/alternatives', input)
  }

  // 2. Rentals
  async listRentals(input: ListRentalsInput): Promise<ListRentalsResponse> {
    return this.http.get<ListRentalsResponse>('/rentals', input)
  }

  async getRental(input: GetRentalInput): Promise<GetRentalResponse> {
    return this.http.get<GetRentalResponse>(`/rentals/${input.id}`)
  }

  async previewPricing(input: PreviewPricingInput): Promise<PreviewPricingResponse> {
    return this.http.post<PreviewPricingResponse>('/rentals/preview_pricing', input)
  }

  async createQuoteDraft(input: CreateQuoteDraftInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>('/rentals/quote', input)
  }

  async updateQuoteDraft(input: UpdateQuoteDraftInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/rentals/${input.rental_id}/update_quote`, input)
  }

  async requestReservation(input: RequestReservationInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/rentals/${input.rental_id}/request_reservation`, input)
  }

  async requestContractApproval(input: RequestContractApprovalInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/rentals/${input.rental_id}/request_contract`, input)
  }

  async getRentalAudit(input: GetRentalAuditInput): Promise<GetRentalAuditResponse> {
    return this.http.get<GetRentalAuditResponse>(`/rentals/${input.rental_id}/audit`)
  }

  // 3. Warehouse
  async startCheckout(input: StartCheckoutInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/checkout/${input.rental_id}/start`, input)
  }

  async scanCheckoutSerial(input: ScanCheckoutSerialInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/checkout/${input.rental_id}/scan`, input)
  }

  async completeCheckout(input: CompleteCheckoutInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/checkout/${input.rental_id}/complete`, input)
  }

  async startCheckin(input: StartCheckinInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/checkin/${input.rental_id}/start`, input)
  }

  async scanCheckinSerial(input: ScanCheckinSerialInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/checkin/${input.rental_id}/scan`, input)
  }

  async markSerialMissing(input: MarkSerialMissingInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/checkin/${input.rental_id}/mark_missing`, input)
  }

  async addDamageEvidence(input: AddDamageEvidenceInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/checkin/${input.rental_id}/damage_evidence`, input)
  }

  async completePartialReturn(input: CompletePartialReturnInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/checkin/${input.rental_id}/complete_partial`, input)
  }

  async lookupScan(input: LookupScanInput): Promise<LookupScanResponse> {
    return this.http.get<LookupScanResponse>('/warehouse/lookup_scan', input)
  }

  // 4. Consignment
  async listOwners(input: ListOwnersInput): Promise<ListOwnersResponse> {
    return this.http.get<ListOwnersResponse>('/consignment/owners', input)
  }

  async getConsignmentDashboard(input: ConsignmentDashboardInput): Promise<ConsignmentDashboardResponse> {
    return this.http.get<ConsignmentDashboardResponse>('/consignment/dashboard', input)
  }

  async getOwnerStatement(input: OwnerStatementInput): Promise<OwnerStatementResponse> {
    return this.http.get<OwnerStatementResponse>(`/consignment/statement/${input.owner_id}/${input.period}`)
  }

  async requestOwnerStatementExport(input: OwnerStatementExportInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>('/consignment/export_statement', input)
  }

  // 5. Approvals
  async listApprovalRequests(input: ListApprovalRequestsInput): Promise<ListApprovalsResponse> {
    return this.http.get<ListApprovalsResponse>('/approvals', input)
  }

  async getApprovalRequest(input: GetApprovalRequestInput): Promise<GetApprovalResponse> {
    return this.http.get<GetApprovalResponse>(`/approvals/${input.id}`)
  }

  async approveApprovalRequest(input: ApproveApprovalInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/approvals/${input.id}/approve`, input)
  }

  async rejectApprovalRequest(input: RejectApprovalInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/approvals/${input.id}/reject`, input)
  }

  // 6. Inbound & Telemetry
  async listInboundRequests(input: ListInboundRequestsInput): Promise<ListInboundRequestsResponse> {
    return this.http.get<ListInboundRequestsResponse>('/intelligence/inbound', input)
  }

  async getInboundRequest(input: GetInboundRequestInput): Promise<GetInboundRequestResponse> {
    return this.http.get<GetInboundRequestResponse>(`/intelligence/inbound/${input.id}`)
  }

  async listAiDrafts(input: ListAiDraftsInput): Promise<ListAiDraftsResponse> {
    return this.http.get<ListAiDraftsResponse>('/intelligence/drafts', input)
  }

  async getAgentActivity(input: GetAgentActivityInput): Promise<AgentActivityResponse> {
    return this.http.get<AgentActivityResponse>('/intelligence/activity', input)
  }

  // 7. Copilot
  async createCopilotSession(input: CreateCopilotSessionInput): Promise<CreateCopilotSessionResponse> {
    return this.http.post<CreateCopilotSessionResponse>('/copilot/session', input)
  }

  async sendCopilotMessage(input: SendCopilotMessageInput): Promise<SendCopilotMessageResponse> {
    return this.http.post<SendCopilotMessageResponse>(`/copilot/session/${input.session_id}/message`, input)
  }

  async getCopilotSession(input: GetCopilotSessionInput): Promise<GetCopilotSessionResponse> {
    return this.http.get<GetCopilotSessionResponse>(`/copilot/session/${input.session_id}`)
  }

  async listCopilotSessions(input: ListCopilotSessionsInput): Promise<ListCopilotSessionsResponse> {
    return this.http.get<ListCopilotSessionsResponse>('/copilot/sessions', input)
  }

  async pinCopilotContext(input: PinCopilotContextInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/copilot/session/${input.session_id}/pin`, input)
  }

  async clearCopilotContext(input: ClearCopilotContextInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>(`/copilot/session/${input.session_id}/clear`, input)
  }

  // 8. Catalog, Fleet, Policies, Audit & Migration
  async listEquipment(input: ListEquipmentInput): Promise<ListEquipmentResponse> {
    return this.http.get<ListEquipmentResponse>('/catalog/equipment', input)
  }

  async getEquipment(input: GetEquipmentInput): Promise<GetEquipmentResponse> {
    return this.http.get<GetEquipmentResponse>(`/catalog/equipment/${input.item_code}`)
  }

  async getSerial(input: GetSerialInput): Promise<GetSerialResponse> {
    return this.http.get<GetSerialResponse>(`/catalog/serial/${input.serial_number}`)
  }

  async listKits(input: ListKitsInput): Promise<ListKitsResponse> {
    return this.http.get<ListKitsResponse>('/catalog/kits', input)
  }

  async listRentalPolicies(input: ListRentalPoliciesInput): Promise<ListRentalPoliciesResponse> {
    return this.http.get<ListRentalPoliciesResponse>('/policies', input)
  }

  async getTeamRoles(input: GetTeamRolesInput): Promise<TeamRolesResponse> {
    return this.http.get<TeamRolesResponse>('/team/roles', input)
  }

  async listMigrationBatches(input: ListMigrationBatchesInput): Promise<MigrationBatchesResponse> {
    return this.http.get<MigrationBatchesResponse>('/migration/batches', input)
  }

  async listAuditEvents(input: ListAuditEventsInput): Promise<ListAuditEventsResponse> {
    return this.http.get<ListAuditEventsResponse>('/audit/events', input)
  }

  // 9. Upload & Evidence
  async createUploadIntent(input: CreateUploadIntentInput): Promise<UploadIntentResponse> {
    return this.http.post<UploadIntentResponse>('/upload/intent', input)
  }

  async registerEvidence(input: RegisterEvidenceInput): Promise<MutationResponse> {
    return this.http.post<MutationResponse>('/upload/register_evidence', input)
  }
}
