import type { ProvenanceMeta } from './common'

export type ApprovalType =
  | 'Contract Confirmation'
  | 'Discount Override'
  | 'Dispute Settlement'
  | 'Credit Limit Increase'
  | 'AI Draft Execution'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired'

export interface ApprovalRequestItem extends ProvenanceMeta {
  id: string
  approval_type: ApprovalType
  status: ApprovalStatus
  title: string
  description: string
  reference_doctype: string
  reference_name: string
  requested_by_type: 'Human' | 'Agent'
  requested_by: string
  threshold_exceeded_details?: string
  before_state?: Record<string, unknown>
  after_state?: Record<string, unknown>
  evidence_ids?: string[]
  created_at: string
  resolved_at?: string
  resolved_by?: string
  rejection_reason?: string
}
