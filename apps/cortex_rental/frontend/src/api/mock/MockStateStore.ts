import { initialCompanies } from './fixtures/companies'
import { initialCustomers } from './fixtures/customers'
import { initialCatalog, initialKits } from './fixtures/catalog'
import { initialSerials } from './fixtures/serials'
import { initialRentals } from './fixtures/rentals'
import { initialOwners, initialConsignmentDashboard, initialOwnerStatements } from './fixtures/consignment'
import { initialApprovals } from './fixtures/approvals'
import { initialInboundRequests } from './fixtures/inbound'
import { initialDrafts } from './fixtures/drafts'
import { initialTelemetryRuns } from './fixtures/telemetry'
import { initialAuditEvents } from './fixtures/audit'
import { initialCopilotMessages } from './fixtures/copilot'
import { initialPolicies, initialMigrationBatches } from './fixtures/admin'

import type {
  RentalTransaction,
  EquipmentItem,
  SerialNumberItem,
  KitPackage,
  ConsignmentOwner,
  OwnerStatementSafe,
  ConsignmentDashboardData,
  ApprovalRequestItem,
  InboundRequestItem,
  AiDraftItem,
  AgentRunTelemetry,
  AuditEvent,
  CopilotMessage,
  RentalPolicy,
  MigrationBatch
} from '@/types/domain'

export class MockStateStore {
  public companies = [...initialCompanies]
  public customers = [...initialCustomers]
  public catalog: EquipmentItem[] = JSON.parse(JSON.stringify(initialCatalog))
  public kits: KitPackage[] = JSON.parse(JSON.stringify(initialKits))
  public serials: SerialNumberItem[] = JSON.parse(JSON.stringify(initialSerials))
  public rentals: RentalTransaction[] = JSON.parse(JSON.stringify(initialRentals))
  public owners: ConsignmentOwner[] = JSON.parse(JSON.stringify(initialOwners))
  public consignmentDashboard: ConsignmentDashboardData = JSON.parse(JSON.stringify(initialConsignmentDashboard))
  public ownerStatements: Record<string, OwnerStatementSafe> = JSON.parse(JSON.stringify(initialOwnerStatements))
  public approvals: ApprovalRequestItem[] = JSON.parse(JSON.stringify(initialApprovals))
  public inboundRequests: InboundRequestItem[] = JSON.parse(JSON.stringify(initialInboundRequests))
  public aiDrafts: AiDraftItem[] = JSON.parse(JSON.stringify(initialDrafts))
  public telemetryRuns: AgentRunTelemetry[] = JSON.parse(JSON.stringify(initialTelemetryRuns))
  public auditEvents: AuditEvent[] = JSON.parse(JSON.stringify(initialAuditEvents))
  public copilotMessages: CopilotMessage[] = JSON.parse(JSON.stringify(initialCopilotMessages))
  public policies: RentalPolicy[] = JSON.parse(JSON.stringify(initialPolicies))
  public migrationBatches: MigrationBatch[] = JSON.parse(JSON.stringify(initialMigrationBatches))

  public reset() {
    this.catalog = JSON.parse(JSON.stringify(initialCatalog))
    this.kits = JSON.parse(JSON.stringify(initialKits))
    this.serials = JSON.parse(JSON.stringify(initialSerials))
    this.rentals = JSON.parse(JSON.stringify(initialRentals))
    this.owners = JSON.parse(JSON.stringify(initialOwners))
    this.consignmentDashboard = JSON.parse(JSON.stringify(initialConsignmentDashboard))
    this.ownerStatements = JSON.parse(JSON.stringify(initialOwnerStatements))
    this.approvals = JSON.parse(JSON.stringify(initialApprovals))
    this.inboundRequests = JSON.parse(JSON.stringify(initialInboundRequests))
    this.aiDrafts = JSON.parse(JSON.stringify(initialDrafts))
    this.telemetryRuns = JSON.parse(JSON.stringify(initialTelemetryRuns))
    this.auditEvents = JSON.parse(JSON.stringify(initialAuditEvents))
    this.copilotMessages = JSON.parse(JSON.stringify(initialCopilotMessages))
    this.policies = JSON.parse(JSON.stringify(initialPolicies))
    this.migrationBatches = JSON.parse(JSON.stringify(initialMigrationBatches))
  }

  public recordAudit(
    action: string,
    entityType: string,
    entityId: string,
    actorId = 'kael@cortex.local',
    actorType: 'Human' | 'Agent' | 'System' = 'Human',
    diffSummary?: string
  ): string {
    const eventId = `DEMO-AUD-${String(this.auditEvents.length + 1).padStart(3, '0')}`
    const newEvent: AuditEvent = {
      id: eventId,
      timestamp: new Date().toISOString(),
      actor: {
        actor_type: actorType,
        actor_id: actorId,
        actor_name: actorType === 'Human' ? 'Kael (Operations Lead)' : 'Cortex AI Agent'
      },
      action,
      entity_type: entityType,
      entity_id: entityId,
      request_id: `req-mock-${Date.now()}`,
      diff_summary: diffSummary
    }
    this.auditEvents.unshift(newEvent)
    return eventId
  }
}
