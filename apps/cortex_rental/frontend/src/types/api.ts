export type MutationStatus =
  | 'processing'
  | 'completed'
  | 'failed'
  | 'approval_required'
  | 'policy_denied'
  | 'conflict'
  | 'stale'

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
