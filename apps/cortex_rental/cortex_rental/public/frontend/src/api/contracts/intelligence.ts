import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const InboundRequestItemSchema = ProvenanceMetaSchema.extend({
  id: z.string(),
  source: z.enum(['email', 'pdf', 'phone_transcript', 'web_form']),
  sender_email: z.string(),
  sender_name: z.string().optional(),
  subject: z.string(),
  raw_body: z.string(),
  received_at: z.string(),
  // null = the extraction recorded no score: shown as "confiance non évaluée".
  overall_confidence: z.number().nullable(),
  extracted_fields: z.object({
    customer_name: z.string().optional(),
    start_date: z.string().optional(),
    end_date: z.string().optional(),
    equipment_mentions: z.array(z.object({
      raw_text: z.string(),
      matched_item_code: z.string().optional(),
      quantity: z.number().nullable().optional(),
      confidence: z.number().nullable().optional()
    })).optional(),
    missing_fields: z.array(z.string())
  }),
  status: z.enum(['new', 'reviewed', 'converted', 'dismissed']),
  converted_rental_id: z.string().optional()
})

export type InboundRequestItem = z.infer<typeof InboundRequestItemSchema>

export const ListInboundRequestsInputSchema = z.object({
  status: z.enum(['new', 'reviewed', 'converted', 'dismissed']).optional(),
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20)
})

export type ListInboundRequestsInput = z.input<typeof ListInboundRequestsInputSchema>

export const ListInboundRequestsResponseSchema = ProvenanceMetaSchema.extend({
  items: z.array(InboundRequestItemSchema),
  total_count: z.number()
})

export type ListInboundRequestsResponse = z.infer<typeof ListInboundRequestsResponseSchema>

export const GetInboundRequestInputSchema = z.object({
  id: z.string()
})

export type GetInboundRequestInput = z.infer<typeof GetInboundRequestInputSchema>

export const GetInboundRequestResponseSchema = InboundRequestItemSchema
export type GetInboundRequestResponse = z.infer<typeof GetInboundRequestResponseSchema>

export const AiDraftItemSchema = ProvenanceMetaSchema.extend({
  id: z.string(),
  draft_type: z.enum(['Quote Draft', 'Schedule Change', 'Email Response', 'Discount Request']),
  title: z.string(),
  ai_state: z.enum(['verified', 'extracted', 'proposed', 'needs_confirmation', 'approval_required', 'approved_executed', 'blocked_by_policy']),
  source_evidence_id: z.string(),
  source_evidence_type: z.string(),
  confidence_score: z.number().nullable(),
  proposed_payload: z.record(z.unknown()),
  target_doctype: z.string(),
  target_name: z.string().optional(),
  created_at: z.string(),
  status: z.enum(['pending_review', 'submitted_approval', 'accepted', 'rejected']),
  rejection_reason: z.string().optional()
})

export type AiDraftItem = z.infer<typeof AiDraftItemSchema>

export const ListAiDraftsInputSchema = z.object({
  status: z.enum(['pending_review', 'submitted_approval', 'accepted', 'rejected']).optional(),
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20)
})

export type ListAiDraftsInput = z.input<typeof ListAiDraftsInputSchema>

export const ListAiDraftsResponseSchema = ProvenanceMetaSchema.extend({
  items: z.array(AiDraftItemSchema),
  total_count: z.number()
})

export type ListAiDraftsResponse = z.infer<typeof ListAiDraftsResponseSchema>

export const GetAgentActivityInputSchema = z.object({
  limit: z.number().optional().default(20)
})

export type GetAgentActivityInput = z.input<typeof GetAgentActivityInputSchema>

export const AgentRunTelemetrySchema = ProvenanceMetaSchema.extend({
  run_id: z.string(),
  agent_name: z.string(),
  started_at: z.string(),
  ended_at: z.string().optional(),
  duration_ms: z.number().optional(),
  model_used: z.string().optional(),
  prompt_tokens: z.number().optional(),
  completion_tokens: z.number().optional(),
  total_cost_cad: z.number().optional(),
  tools_invoked: z.array(z.object({
    tool_name: z.string(),
    latency_ms: z.number().optional(),
    status: z.enum(['success', 'error']),
    error_message: z.string().optional()
  })),
  status: z.enum(['completed', 'failed', 'gated', 'running'])
})

export type AgentRunTelemetry = z.infer<typeof AgentRunTelemetrySchema>

export const AgentActivityResponseSchema = ProvenanceMetaSchema.extend({
  runs: z.array(AgentRunTelemetrySchema),
  total_runs: z.number().optional(),
  total_runs_today: z.number().optional(),
  total_cost_today_cad: z.number().optional(),
  avg_latency_ms: z.number().optional()
})

export type AgentActivityResponse = z.infer<typeof AgentActivityResponseSchema>
