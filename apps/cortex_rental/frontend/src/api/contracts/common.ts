import { z } from 'zod'

export const MutationStatusSchema = z.enum([
  'processing',
  'completed',
  'failed',
  'approval_required',
  'policy_denied',
  'conflict',
  'stale'
])

export type MutationStatus = z.infer<typeof MutationStatusSchema>

export const ApiErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  field: z.string().optional(),
  details: z.record(z.unknown()).optional()
})

export type ApiError = z.infer<typeof ApiErrorSchema>

export const PolicyResultSchema = z.object({
  policy_name: z.string(),
  policy_version: z.string().optional(),
  explanation: z.string(),
  next_allowed_action: z.string().optional()
})

export type PolicyResult = z.infer<typeof PolicyResultSchema>

export const MutationResponseSchema = z.object({
  request_id: z.string(),
  entity_id: z.string().optional(),
  status: MutationStatusSchema,
  policy_result: PolicyResultSchema.optional(),
  approval_required: z.boolean(),
  approval_request_id: z.string().optional(),
  audit_event_id: z.string().optional(),
  stale_context: z.boolean().optional(),
  mutation_performed: z.boolean(),
  errors: z.array(ApiErrorSchema).optional()
})

export type MutationResponse = z.infer<typeof MutationResponseSchema>

export const DataProvenanceSchema = z.enum(['demo', 'mock', 'api', 'realtime', 'stale'])
export type DataProvenance = z.infer<typeof DataProvenanceSchema>

export const ProvenanceMetaSchema = z.object({
  provenance: DataProvenanceSchema,
  last_synced_at: z.string(),
  etag: z.string().optional(),
  version: z.number().optional()
})

export type ProvenanceMeta = z.infer<typeof ProvenanceMetaSchema>
