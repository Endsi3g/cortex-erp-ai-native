export type CanonicalAiState =
  | 'verified'           // Confirmed by Cortex backend in real-time
  | 'extracted'          // Extracted from source (email/PDF) with proof
  | 'proposed'           // AI suggestion without business mutation
  | 'needs_confirmation' // Ambiguous/incomplete or below confidence threshold
  | 'approval_required'  // Ready action requiring authorized human approval
  | 'approved_executed'  // Human-approved, backend-executed, and audited
  | 'blocked_by_policy'  // Rejected by policy, permission, or conflict

export type CopilotState =
  | 'idle'
  | 'loading'
  | 'tool_running'
  | 'verified'
  | 'extracted'
  | 'proposed'
  | 'needs_confirmation'
  | 'approval_required'
  | 'completed'
  | 'blocked_by_policy'
  | 'stale'
  | 'failed'
  | 'permission_denied'
  | 'service_unavailable'

export interface AiEvidenceRef {
  id: string
  source_type: 'email' | 'pdf' | 'audio' | 'document' | 'frappe_doc'
  source_name: string
  snippet?: string
  confidence_score: number // 0.00 to 1.00
  extracted_at: string
  sha256_hash?: string
  url?: string
}

export interface AiConfidenceMeta {
  score: number
  is_verified: boolean
  source_field?: string
  evidence_ref?: AiEvidenceRef
}
