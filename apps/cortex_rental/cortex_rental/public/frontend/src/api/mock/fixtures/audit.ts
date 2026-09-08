import type { AuditEvent } from '@/types/audit'

export const initialAuditEvents: AuditEvent[] = [
  {
    id: 'DEMO-AUD-001',
    timestamp: '2026-09-01T08:15:00Z',
    actor: {
      actor_type: 'Human',
      actor_id: 'marc.warehouse@cortex.demo',
      actor_name: 'Marc-André (Warehouse Lead)',
      ip_address: '192.168.1.42'
    },
    action: 'cortex.rental.checkout_completed',
    entity_type: 'Cortex Rental Transaction',
    entity_id: 'DEMO-TRX-2026-001',
    request_id: 'req-chk-882194',
    policy_execution: {
      policy_name: 'Rental Dispatch Readiness Check',
      policy_version: 'v2.1',
      passed: true,
      rule_evaluation_summary: 'All required serial numbers scanned; account in good standing.'
    },
    before_state: {
      rental_state: 'Contract',
      scanned_count: 0
    },
    after_state: {
      rental_state: 'Checked Out',
      scanned_count: 2
    },
    diff_summary: 'Status changed from Contract to Checked Out. 2 serials assigned.',
    evidence_hash_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
  },
  {
    id: 'DEMO-AUD-002',
    timestamp: '2026-09-01T11:20:00Z',
    actor: {
      actor_type: 'Agent',
      actor_id: 'agent.intake@cortex.ai',
      actor_name: 'Cortex Intake Agent'
    },
    action: 'cortex.rental.quote_draft_created',
    entity_type: 'Cortex Rental Transaction',
    entity_id: 'DEMO-TRX-2026-003',
    request_id: 'req-intake-990142',
    diff_summary: 'Quote Draft DEMO-TRX-2026-003 generated from Inbound Email DEMO-INB-001.',
    evidence_hash_sha256: '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945'
  }
]
