import type { ProvenanceMeta } from './common'
import type { CanonicalAiState, CopilotState } from './ai'

export interface InboundRequestItem extends ProvenanceMeta {
  id: string
  source: 'email' | 'pdf' | 'phone_transcript' | 'web_form'
  sender_email: string
  sender_name?: string
  subject: string
  raw_body: string
  received_at: string
  overall_confidence: number // 0.00 to 1.00
  extracted_fields: {
    customer_name?: string
    start_date?: string
    end_date?: string
    equipment_mentions?: Array<{
      raw_text: string
      matched_item_code?: string
      quantity?: number
      confidence: number
    }>
    missing_fields: string[]
  }
  status: 'new' | 'reviewed' | 'converted' | 'dismissed'
  converted_rental_id?: string
}

export interface AiDraftItem extends ProvenanceMeta {
  id: string
  draft_type: 'Quote Draft' | 'Schedule Change' | 'Email Response' | 'Discount Request'
  title: string
  ai_state: CanonicalAiState
  source_evidence_id: string
  source_evidence_type: string
  confidence_score: number
  proposed_payload: Record<string, unknown>
  target_doctype: string
  target_name?: string
  created_at: string
  status: 'pending_review' | 'submitted_approval' | 'accepted' | 'rejected'
  rejection_reason?: string
}

export interface AgentRunTelemetry extends ProvenanceMeta {
  run_id: string
  agent_name: 'Cortex Intake' | 'Cortex Availability' | 'Cortex Consignment' | 'Cortex Copilot'
  started_at: string
  ended_at: string
  duration_ms: number
  model_used: 'gemini-2.5-pro' | 'claude-3-5-sonnet' | 'gemini-2.5-flash'
  prompt_tokens: number
  completion_tokens: number
  total_cost_cad: number
  tools_invoked: Array<{
    tool_name: string
    latency_ms: number
    status: 'success' | 'error'
    error_message?: string
  }>
  status: 'completed' | 'failed' | 'gated'
}

export interface CopilotMessage {
  id: string
  session_id: string
  sender: 'user' | 'assistant' | 'system'
  content: string
  state: CopilotState
  timestamp: string
  tools_called?: Array<{
    name: string
    params: Record<string, unknown>
    result_preview?: string
  }>
  evidence_refs?: Array<{
    id: string
    name: string
    confidence: number
  }>
  action_proposal?: {
    action_type: string
    payload: Record<string, unknown>
    requires_approval: boolean
  }
}
