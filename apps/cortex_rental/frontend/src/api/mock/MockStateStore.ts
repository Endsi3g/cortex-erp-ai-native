import { initialCompanies } from './fixtures/companies'
import { initialCustomers } from './fixtures/customers'
import { initialCatalog, initialKits } from './fixtures/catalog'
import { initialSerials } from './fixtures/serials'
import { initialRentals } from './fixtures/rentals'
import { initialOwners, initialConsignmentDashboard, initialOwnerStatements } from './fixtures/consignment'
import { initialApprovals } from './fixtures/approvals'
import { initialAuditEvents } from './fixtures/audit'
import { initialInboxRows, initialInboundDetails, initialAgentRuns } from './fixtures/ai'
import type { AgentRun, InboundDetail, InboxItem } from '@/api/contracts/ai'
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
  AuditEvent,
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
  public inboxRows: InboxItem[] = JSON.parse(JSON.stringify(initialInboxRows))
  public inboundDetails: InboundDetail[] = JSON.parse(JSON.stringify(initialInboundDetails))
  public agentRuns: AgentRun[] = JSON.parse(JSON.stringify(initialAgentRuns))
  public auditEvents: AuditEvent[] = JSON.parse(JSON.stringify(initialAuditEvents))
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
    this.inboxRows = JSON.parse(JSON.stringify(initialInboxRows))
    this.inboundDetails = JSON.parse(JSON.stringify(initialInboundDetails))
    this.agentRuns = JSON.parse(JSON.stringify(initialAgentRuns))
    this.auditEvents = JSON.parse(JSON.stringify(initialAuditEvents))
    this.policies = JSON.parse(JSON.stringify(initialPolicies))
    this.migrationBatches = JSON.parse(JSON.stringify(initialMigrationBatches))
  }

  /** Inbox = inbound/draft rows + approval rows derived from the approvals fixture. */
  public get inbox(): InboxItem[] {
    const state = { pending: 'needs_review', approved: 'validated', rejected: 'rejected' } as Record<string, InboxItem['state']>
    const approvals: InboxItem[] = this.approvals.map(a => ({
      id: `approval:${a.id}`,
      kind: 'approval',
      source_id: a.id,
      title: a.title,
      summary: a.description,
      reference: `${a.reference_doctype} ${a.reference_name}`,
      customer: this.rentals.find(r => r.id === a.reference_name)?.customer_name ?? '',
      agent: a.requested_by_type === 'Agent' ? a.requested_by : null,
      requested_by: a.requested_by,
      requested_by_type: a.requested_by_type,
      state: state[a.status] ?? 'expired',
      confidence: null,
      priority: a.approval_type === 'Contract Confirmation' ? 'high' : 'normal',
      created_at: a.created_at.replace('T', ' ').replace('Z', '')
    }))
    return [...approvals, ...this.inboxRows].sort((x, y) => y.created_at.localeCompare(x.created_at))
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
