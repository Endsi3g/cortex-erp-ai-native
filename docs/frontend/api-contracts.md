# Cortex ERP AI-Native — API Contracts Specification

## 1. Overview & Architectural Principles

All communications between the Vue 3 frontend and Frappe / Cortex backend must strictly implement the typed `CortexApiClient` interface.

### Non-Negotiable Rules:
1. **No direct HTTP calls outside `CortexApiClient`**: Components invoke client methods; adapters handle network transport, CSRF headers, and serialization.
2. **Every mutation returns a `MutationResponse` envelope**: Guarantees auditability (`audit_event_id`, `request_id`), human supervision gating (`approval_required`, `approval_request_id`), and policy explanation (`policy_result`).
3. **Hermetic Mock Isolation**: Development/demo builds use `MockCortexApiClient` with `DEMO-` prefixed fixtures, realistic simulated latency (150ms - 1500ms), and controllable error injection.
4. **Data Provenance Metadata**: Responses tag data with `demo`, `mock`, `api`, `realtime`, or `stale`.

---

## 2. Core Mutation Envelope Contract

```typescript
export type MutationStatus =
  | 'processing'        // Asynchronously running in background queue
  | 'completed'         // Successfully executed and written to DB
  | 'failed'            // Validation or execution failure
  | 'approval_required' // Action blocked pending human supervisor approval
  | 'policy_denied'     // Blocked by a pricing, readiness, or safety policy
  | 'conflict'          // Temporal availability or serial conflict
  | 'stale'             // Entity version mismatch (concurrency guard)

export interface ApiError {
  code: string
  message: string
  field?: string
  details?: Record<string, unknown>
}

export interface PolicyResult {
  policy_name: string
  policy_version?: string
  explanation: string
  next_allowed_action?: string
}

export interface MutationResponse {
  request_id: string
  entity_id?: string
  status: MutationStatus
  policy_result?: PolicyResult
  approval_required: boolean
  approval_request_id?: string
  audit_event_id?: string
  stale_context?: boolean
  mutation_performed: boolean
  errors?: ApiError[]
}

export type DataProvenance = 'demo' | 'mock' | 'api' | 'realtime' | 'stale'
```

---

## 3. The 32 Canonical Methods of `CortexApiClient`

```typescript
export interface CortexApiClient {
  // 1. Availability & Inventory
  getAvailabilityMatrix(input: AvailabilityMatrixInput): Promise<AvailabilityMatrixResponse>
  checkInventoryAvailability(input: AvailabilityCheckInput): Promise<AvailabilityCheckResponse>
  getAvailabilityAlternatives(input: AlternativesInput): Promise<AlternativesResponse>

  // 2. Rentals Lifecycle & Composer
  listRentals(input: ListRentalsInput): Promise<ListRentalsResponse>
  getRental(input: GetRentalInput): Promise<GetRentalResponse>
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
  requestOwnerStatementExport(input: OwnerStatementExportInput): Promise<MutationResponse>

  // 5. Human Supervision & Approval Queue SAS
  listApprovalRequests(input: ListApprovalRequestsInput): Promise<ListApprovalsResponse>
  getApprovalRequest(input: GetApprovalRequestInput): Promise<GetApprovalResponse>
  approveApprovalRequest(input: ApproveApprovalInput): Promise<MutationResponse>
  rejectApprovalRequest(input: RejectApprovalInput): Promise<MutationResponse>

  // 6. Inbound Intake, AI Drafts & Telemetry
  listInboundRequests(input: ListInboundRequestsInput): Promise<ListInboundRequestsResponse>
  getInboundRequest(input: GetInboundRequestInput): Promise<GetInboundRequestResponse>
  listAiDrafts(input: ListAiDraftsInput): Promise<ListAiDraftsResponse>
  getAgentActivity(input: GetAgentActivityInput): Promise<AgentActivityResponse>

  // 7. Contextual Copilot & Assistant Gateway
  createCopilotSession(input: CreateCopilotSessionInput): Promise<CreateCopilotSessionResponse>
  sendCopilotMessage(input: SendCopilotMessageInput): Promise<SendCopilotMessageResponse>
  getCopilotSession(input: GetCopilotSessionInput): Promise<GetCopilotSessionResponse>
  listCopilotSessions(input: ListCopilotSessionsInput): Promise<ListCopilotSessionsResponse>
  pinCopilotContext(input: PinCopilotContextInput): Promise<MutationResponse>
  clearCopilotContext(input: ClearCopilotContextInput): Promise<MutationResponse>

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
}
```

---

## 4. Privacy Contract: `OwnerStatementSafe`

To protect customer confidentiality, equipment owner statements must strictly adhere to `OwnerStatementSafe`:

```typescript
export interface OwnerStatementSafe {
  owner: {
    id: string
    display_name: string
    code: string
  }
  period: {
    start: string
    end: string
    timezone: string
  }
  currency: 'CAD'
  totals: {
    eligible_net_revenue: number
    owner_amount_due: number
  }
  lines: Array<{
    serial_number: string
    equipment_name: string
    rental_start_date: string
    rental_end_date: string
    billable_days: number
    rate: number
    discount_amount: number
    consignment_percentage: number
    owner_amount: number
    invoice_reference: string
  }>
  generated_at: string
  snapshot_version: string
}
```

Forbidden fields in any consignment data:
- `customer_name`, `customer_email`, `customer_phone`, `customer_address`, `customer_id`
- `customer_payment_information`, `customer_language`, `project_name`, `project_notes`
- `communication_body`, `customer_document`, `customer_file_url`, `customer_contact`
