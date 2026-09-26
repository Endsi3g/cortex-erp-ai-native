export interface AuditActor {
  actor_type: 'Human' | 'Agent' | 'System'
  actor_id: string
  actor_name?: string
  ip_address?: string
  user_agent?: string
}

export interface AuditPolicyExecution {
  policy_name: string
  policy_version: string
  passed: boolean
  rule_evaluation_summary: string
}

export interface AuditEvent {
  id: string
  timestamp: string
  actor: AuditActor
  action: string
  entity_type: string
  entity_id: string
  request_id: string
  policy_execution?: AuditPolicyExecution
  before_state?: Record<string, unknown>
  after_state?: Record<string, unknown>
  diff_summary?: string
  evidence_hash_sha256?: string
  evidence_url?: string
}
