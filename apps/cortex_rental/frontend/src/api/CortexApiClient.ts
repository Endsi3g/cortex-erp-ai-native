import type {
  RentalSummary,
  ListRentalSummariesInput,
  ReadinessField,
  OperationsOverview,
  InvoiceRow,
  PaymentRow,
  PagedResult,
  ListInvoicesInput,
  ListPaymentsInput,
  RentalBilling,
  PaymentMode,
  RecordAdvanceInput,
  RecordAdvanceResult,
  PnlFilterOptions,
  PnlFilters,
  PnlReport,
  GlobalSearchResponse,
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
} from './contracts'
import type { InboxKind, InboxList, InboxDetail, AgentActivity, AgentActivityInput, AssistantStatus, ChatSessionSummary, ChatSessionDetail, SendChatInput, SendChatResult } from './contracts/ai'

export interface CortexApiClient {
  // 1. Availability & Inventory
  getAvailabilityMatrix(input: AvailabilityMatrixInput): Promise<AvailabilityMatrixResponse>
  checkInventoryAvailability(input: AvailabilityCheckInput): Promise<AvailabilityCheckResponse>
  getAvailabilityAlternatives(input: AlternativesInput): Promise<AlternativesResponse>

  // 2. Rentals Lifecycle & Composer
  listRentals(input: ListRentalsInput): Promise<ListRentalsResponse>
  getRental(input: GetRentalInput): Promise<GetRentalResponse>
  searchRentalCustomers(query: string): Promise<RentalCustomerOption[]>
  searchRentalCatalog(query: string): Promise<RentalCatalogOption[]>
  previewPricing(input: PreviewPricingInput): Promise<PreviewPricingResponse>
  createQuoteDraft(input: CreateQuoteDraftInput): Promise<MutationResponse>
  updateQuoteDraft(input: UpdateQuoteDraftInput): Promise<MutationResponse>
  requestReservation(input: RequestReservationInput): Promise<MutationResponse>
  requestContractApproval(input: RequestContractApprovalInput): Promise<MutationResponse>
  getRentalAudit(input: GetRentalAuditInput): Promise<GetRentalAuditResponse>

  // 3. Warehouse Field Operations (Check-out & Check-in)
  startCheckout(input: StartCheckoutInput): Promise<MutationResponse>
  scanCheckoutSerial(input: ScanCheckoutSerialInput): Promise<MutationResponse>
  completeCheckout(input: CompleteCheckoutInput): Promise<MutationResponse>
  startCheckin(input: StartCheckinInput): Promise<MutationResponse>
  scanCheckinSerial(input: ScanCheckinSerialInput): Promise<MutationResponse>
  markSerialMissing(input: MarkSerialMissingInput): Promise<MutationResponse>
  addDamageEvidence(input: AddDamageEvidenceInput): Promise<MutationResponse>
  completePartialReturn(input: CompletePartialReturnInput): Promise<MutationResponse>
  lookupScan(input: LookupScanInput): Promise<LookupScanResponse>

  // 4. Consignment & Owner Statements (Anti-PII Leakage)
  listOwners(input: ListOwnersInput): Promise<ListOwnersResponse>
  getConsignmentDashboard(input: ConsignmentDashboardInput): Promise<ConsignmentDashboardResponse>
  getOwnerStatement(input: OwnerStatementInput): Promise<OwnerStatementResponse>

  // 5. Human Supervision & Approval Queue SAS
  listApprovalRequests(input: ListApprovalRequestsInput): Promise<ListApprovalsResponse>
  getApprovalRequest(input: GetApprovalRequestInput): Promise<GetApprovalResponse>
  approveApprovalRequest(input: ApproveApprovalInput): Promise<MutationResponse>
  rejectApprovalRequest(input: RejectApprovalInput): Promise<MutationResponse>

  // 6. AI — inbox (approvals, inbound requests, agent drafts) and agent activity
  listInbox(kind?: InboxKind, includeClosed?: boolean): Promise<InboxList>
  getInboxItem(kind: InboxKind, sourceId: string): Promise<InboxDetail>
  rejectInbound(sourceId: string, reason: string): Promise<void>
  linkInboundToRental(sourceId: string, rentalId: string): Promise<void>
  listAgentActivity(input: AgentActivityInput): Promise<AgentActivity>

  // 7. Assistant (chat gateway — the server picks the agent from the page)
  getAssistantStatus(): Promise<AssistantStatus>
  sendChatMessage(input: SendChatInput): Promise<SendChatResult>
  getChatSession(sessionId: string): Promise<ChatSessionDetail>
  listChatSessions(): Promise<ChatSessionSummary[]>

  // 8. Catalog, Fleet, Policies, Audit & Migration
  listEquipment(input: ListEquipmentInput): Promise<ListEquipmentResponse>
  getEquipment(input: GetEquipmentInput): Promise<GetEquipmentResponse>
  getSerial(input: GetSerialInput): Promise<GetSerialResponse>
  listKits(input: ListKitsInput): Promise<ListKitsResponse>
  listRentalPolicies(input: ListRentalPoliciesInput): Promise<ListRentalPoliciesResponse>
  getTeamRoles(input: GetTeamRolesInput): Promise<TeamRolesResponse>
  listMigrationBatches(input: ListMigrationBatchesInput): Promise<MigrationBatchesResponse>
  listAuditEvents(input: ListAuditEventsInput): Promise<ListAuditEventsResponse>

  // 9. Upload & Evidence Registration
  createUploadIntent(input: CreateUploadIntentInput): Promise<UploadIntentResponse>
  registerEvidence(input: RegisterEvidenceInput): Promise<MutationResponse>

  // 10. Finance (ERPNext reports)
  getPnlFilterOptions(): Promise<PnlFilterOptions>
  getProfitAndLoss(filters: PnlFilters): Promise<PnlReport>

  // 11. Global search (⌘K)
  globalSearch(query: string): Promise<GlobalSearchResponse>

  // 12. Billing (ERPNext Sales Order / Payment Entry / Sales Invoice)
  listInvoices(input: ListInvoicesInput): Promise<PagedResult<InvoiceRow>>
  listPayments(input: ListPaymentsInput): Promise<PagedResult<PaymentRow>>
  getRentalBilling(rentalId: string): Promise<RentalBilling>
  getPaymentModes(): Promise<PaymentMode[]>
  recordAdvancePayment(input: RecordAdvanceInput): Promise<RecordAdvanceResult>
  createFinalInvoice(rentalId: string): Promise<{ sales_invoice: string }>

  // 13. Operations & rental lifecycle
  listRentalSummaries(input: ListRentalSummariesInput): Promise<PagedResult<RentalSummary>>
  getOperationsOverview(day?: string): Promise<OperationsOverview>
  setReadiness(rentalId: string, field: ReadinessField, value: boolean, note?: string): Promise<GetRentalResponse>
  cancelRental(rentalId: string, reason: string): Promise<GetRentalResponse>
  closeRental(rentalId: string): Promise<GetRentalResponse>

  // 14. Evidence files (private Frappe File attached to the rental)
  uploadRentalEvidence(rentalId: string, file: File): Promise<{ file_name: string; file_url: string }>

  // 15. Catalog mutations (catalog managers, audited)
  updateEquipmentProfile(itemCode: string, changes: EquipmentProfileChanges): Promise<GetEquipmentResponse>
  setSerialStatus(serialNo: string, status: SerialStatus, reason: string): Promise<GetSerialResponse>
  saveKit(kit: RentalKit): Promise<RentalKit>

  // 16. Consignment workflow & customers (staff)
  getOwner(ownerId: string, period?: string): Promise<ConsignmentOwnerRecord>
  saveOwner(owner: OwnerDraft): Promise<ConsignmentOwnerRecord>
  setSerialOwner(serialNo: string, ownerId: string | null): Promise<void>
  prepareStatement(ownerId: string, period: string): Promise<void>
  approveStatement(ownerId: string, period: string): Promise<void>
  markStatementPaid(ownerId: string, period: string, reference: string): Promise<void>
  listCustomers(input: ListCustomersInput): Promise<ListCustomersResponse>
  getCustomer(customer: string): Promise<CustomerRecord>
  createCustomer(input: NewCustomerInput): Promise<CustomerRecord>
  setCustomerInsurance(customer: string, validUntil: string | null, note?: string): Promise<CustomerRecord>
}
