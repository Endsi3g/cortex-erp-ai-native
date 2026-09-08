import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const CopilotStateSchema = z.enum([
  'idle',
  'loading',
  'tool_running',
  'verified',
  'extracted',
  'proposed',
  'needs_confirmation',
  'approval_required',
  'completed',
  'blocked_by_policy',
  'stale',
  'failed',
  'permission_denied',
  'service_unavailable'
])

export const CopilotMessageSchema = z.object({
  id: z.string(),
  session_id: z.string(),
  sender: z.enum(['user', 'assistant', 'system']),
  content: z.string(),
  state: CopilotStateSchema,
  timestamp: z.string(),
  tools_called: z.array(z.object({
    name: z.string(),
    params: z.record(z.unknown()),
    result_preview: z.string().optional()
  })).optional(),
  evidence_refs: z.array(z.object({
    id: z.string(),
    name: z.string(),
    confidence: z.number()
  })).optional(),
  action_proposal: z.object({
    action_type: z.string(),
    payload: z.record(z.unknown()),
    requires_approval: z.boolean()
  }).optional()
})

export type CopilotMessage = z.infer<typeof CopilotMessageSchema>

export const CreateCopilotSessionInputSchema = z.object({
  context_entity_type: z.string().optional(),
  context_entity_id: z.string().optional()
})

export type CreateCopilotSessionInput = z.infer<typeof CreateCopilotSessionInputSchema>

export const CreateCopilotSessionResponseSchema = ProvenanceMetaSchema.extend({
  session_id: z.string(),
  created_at: z.string(),
  messages: z.array(CopilotMessageSchema)
})

export type CreateCopilotSessionResponse = z.infer<typeof CreateCopilotSessionResponseSchema>

export const SendCopilotMessageInputSchema = z.object({
  session_id: z.string(),
  content: z.string(),
  context_entity_type: z.string().optional(),
  context_entity_id: z.string().optional()
})

export type SendCopilotMessageInput = z.infer<typeof SendCopilotMessageInputSchema>

export const SendCopilotMessageResponseSchema = ProvenanceMetaSchema.extend({
  user_message: CopilotMessageSchema,
  assistant_message: CopilotMessageSchema
})

export type SendCopilotMessageResponse = z.infer<typeof SendCopilotMessageResponseSchema>

export const GetCopilotSessionInputSchema = z.object({
  session_id: z.string()
})

export type GetCopilotSessionInput = z.infer<typeof GetCopilotSessionInputSchema>

export const GetCopilotSessionResponseSchema = CreateCopilotSessionResponseSchema
export type GetCopilotSessionResponse = z.infer<typeof GetCopilotSessionResponseSchema>

export const ListCopilotSessionsInputSchema = z.object({
  limit: z.number().optional().default(10)
})

export type ListCopilotSessionsInput = z.infer<typeof ListCopilotSessionsInputSchema>

export const ListCopilotSessionsResponseSchema = ProvenanceMetaSchema.extend({
  sessions: z.array(z.object({
    session_id: z.string(),
    created_at: z.string(),
    last_message_preview: z.string(),
    context_entity_type: z.string().optional(),
    context_entity_id: z.string().optional()
  }))
})

export type ListCopilotSessionsResponse = z.infer<typeof ListCopilotSessionsResponseSchema>

export const PinCopilotContextInputSchema = z.object({
  session_id: z.string(),
  entity_type: z.string(),
  entity_id: z.string(),
  entity_title: z.string()
})

export type PinCopilotContextInput = z.infer<typeof PinCopilotContextInputSchema>

export const ClearCopilotContextInputSchema = z.object({
  session_id: z.string()
})

export type ClearCopilotContextInput = z.infer<typeof ClearCopilotContextInputSchema>
