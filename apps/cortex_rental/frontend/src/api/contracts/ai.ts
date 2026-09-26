/**
 * AI contracts — cortex_rental.api.v1.ai (Inbox, Workspace, Audit) and
 * cortex_rental.api.v1.chat (assistant). Chat blocks mirror
 * schemas/chat_schemas.py on the server.
 */
import type { GetRentalResponse } from './rentals'

export type InboxKind = 'approval' | 'inbound' | 'draft'
export type InboxState =
  | 'processing' | 'ready' | 'low_confidence' | 'needs_review' | 'validated'
  | 'rejected' | 'applied' | 'extraction_error' | 'expired'

export interface InboxItem extends Record<string, unknown> {
  id: string
  kind: InboxKind
  source_id: string
  title: string
  summary: string
  reference: string
  customer: string
  agent: string | null
  requested_by: string | null
  requested_by_type: 'Agent' | 'Human' | 'External'
  state: InboxState
  /** Model score as recorded by the extraction run; null when none was produced. Never calibrated. */
  confidence: number | null
  priority: 'low' | 'normal' | 'high'
  created_at: string
  amount?: number
}

export interface InboxList {
  provenance?: 'api' | 'mock'
  items: InboxItem[]
  can_decide_approvals: boolean
  team_scope_available: boolean
}

export interface InboundDetail {
  kind: 'inbound'
  id: string
  status: string
  subject: string
  sender_email: string
  source_channel: string
  received_at: string
  raw_text: string
  extracted_transaction: string | null
  evidence: Array<{ id: string; channel: string; excerpt: string; sha256: string; mime_type: string | null; scanned_clean: boolean; has_file: boolean }>
  extraction: null | {
    id: string
    schema_version: string
    validation_status: 'Valid' | 'Invalid'
    validation_errors: string[]
    overall_confidence: number | null
    calibrated: false
    review_required: boolean
    model: string | null
    agent: string
    extracted_at: string
    payload: {
      customer?: { name?: string; company_name?: string | null; email?: string | null; phone?: string | null; confidence?: number }
      rental_period?: { starts_at?: string; ends_at?: string; confidence?: number }
      items?: Array<{ raw_text: string; quantity: number; matched_item_code?: string | null; matched_item_id?: string | null; confidence?: number }>
      pricing_hints?: { requested_discount_percent?: number | null; budget_limit?: number | null; notes?: string | null }
      metadata?: Record<string, unknown>
    }
    missing_fields: string[]
  }
}

export interface DraftDetail {
  kind: 'draft'
  rental: GetRentalResponse
}

export interface ApprovalDetail {
  kind: 'approval'
  row: InboxItem
  status: 'Pending' | 'Approved' | 'Rejected' | 'Expired'
  entity_type: string
  entity_id: string
  proposed: Record<string, unknown>
  current: Record<string, unknown>
  evidence_ids: string[]
  policy_decision: Record<string, unknown>
  decided_by: string | null
  decided_at: string | null
  decision_reason: string | null
  self_requested: boolean
}

export type InboxDetail = InboundDetail | DraftDetail | ApprovalDetail

export interface AgentToolCall {
  tool_name: string
  scope: string | null
  status: 'Success' | 'Denied' | 'Error'
  started_at: string
  duration_ms: number | null
  error: string | null
}

export interface AgentRun extends Record<string, unknown> {
  id: string
  agent: string
  request_id: string
  actor: string
  model: string | null
  status: 'Running' | 'Completed' | 'Failed'
  tool_call_count: number
  started_at: string
  last_seen_at: string | null
  tool_calls: AgentToolCall[]
}

export interface AgentActivityInput {
  agent?: string
  status?: string
  from_date?: string
  to_date?: string
  page: number
  page_size: number
}

export interface AgentActivity {
  provenance?: 'api' | 'mock'
  items: AgentRun[]
  total_count: number
  page: number
  page_size: number
  agents: string[]
}

// ---- Assistant (chat) ---------------------------------------------------------

export interface AssistantStatus {
  available: boolean
  provider: 'anthropic' | 'onyx' | 'mock'
  model_name: string | null
}

export type ChatBlock =
  | { type: 'assistant_text'; text: string; source_ids: string[] }
  | { type: 'verified_fact'; title: string; items: string[]; source_ids: string[]; checked_at: string }
  | { type: 'extracted_data'; title: string; fields: Array<{ label: string; value: string; confidence: 'high' | 'medium' | 'low'; evidence_id?: string | null }> }
  | { type: 'proposal'; title: string; summary: string; impact: string[]; action: 'open_quote_composer' | 'create_quote_draft'; draft_id?: string | null; requires_approval: boolean }
  | { type: 'approval_required'; approval_request_id: string; action_label: string; requirements: Array<{ label: string; passed: boolean }>; evidence_ids: string[] }
  | { type: 'risk'; severity: 'info' | 'warning' | 'danger'; title: string; explanation: string; source_ids: string[] }
  | { type: 'missing_information'; fields: string[]; suggested_next_action?: string | null }
  | { type: 'tool_progress'; tool_name: string; state: 'running' | 'success' | 'failed'; message: string }
  | { type: 'error'; title: string; safe_message: string; retry_allowed: boolean }
  | { type: 'widget'; tool: string; view: WidgetView; data: unknown }
  | ActionProposal
  | { type: 'page_link'; route: string; label: string }

/** How the UI should render a read tool's result (see services/ai/tools.py). */
export interface WidgetView {
  type?: 'table' | 'record' | 'kpis' | 'availability' | 'pricing' | 'report' | 'link'
  entity?: string
  id?: string
  [key: string]: unknown
}

export interface ActionProposal {
  type: 'action_proposal'
  action_id: string
  tool: string
  title: string
  impact: string[]
  effect: string
  arguments: Record<string, unknown>
  status: 'proposed' | 'executed' | 'cancelled' | 'failed' | 'expired'
  result?: Record<string, unknown> | null
  error?: string | null
}

/** Streaming event published by the server on the `cortex_ai` realtime channel. */
export interface AssistantStreamEvent {
  session: string
  turn: string | null
  kind: 'text' | 'tool' | 'block' | 'done' | 'error'
  delta?: string
  tool?: string
  state?: 'running' | 'success' | 'failed'
  type?: string
  message?: string
  message_id?: string
  [key: string]: unknown
}

export interface ChatMessage {
  id: string
  sender_type: 'Human' | 'Agent' | 'System'
  text: string
  blocks: ChatBlock[]
  model_name?: string | null
  created_at: string
  /** Client-only: the answer is still streaming in. */
  streaming?: boolean
  /** Client-only: tool currently running during streaming. */
  activeTool?: string | null
}

export interface ChatSessionSummary {
  name: string
  agent_profile: string
  state: 'Active' | 'Closed'
  started_at: string
  last_message_at: string | null
  title: string
}

export interface ChatSessionDetail {
  name: string
  agent_profile: string
  state: 'Active' | 'Closed'
  messages: ChatMessage[]
}

/** What the page shows right now (the server re-checks access to every id). */
export interface ChatContext {
  page: string
  active_doctype?: string
  active_document_name?: string
  selected_item_codes?: string[]
  selected_serial_nos?: string[]
  visible_date_range?: { start: string; end: string }
  active_filters?: Record<string, unknown>
  locale: 'fr-CA' | 'en-CA'
}

export interface SendChatInput {
  chat_session_id?: string
  message: string
  context: ChatContext
  /** Echoed in streaming events so the UI can match them to this turn. */
  client_turn_id?: string
}

export interface SendChatResult {
  message_id: string
  chat_session_id: string
  status: 'completed' | 'processing'
  blocks: ChatBlock[]
}

export interface ActionDecision {
  action_id: string
  status: 'executed' | 'cancelled' | 'failed'
  result: (Record<string, unknown> & { route?: string }) | null
  error: string | null
}
