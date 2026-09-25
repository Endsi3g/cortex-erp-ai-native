import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const RentalPolicySchema = ProvenanceMetaSchema.extend({
  name: z.string(),
  policy_name: z.string(),
  version: z.string(),
  description: z.string(),
  rules: z.array(z.object({
    rule_key: z.string(),
    rule_description: z.string(),
    value: z.string()
  })),
  effective_from: z.string(),
  is_active: z.boolean()
})

export type RentalPolicy = z.infer<typeof RentalPolicySchema>

export const ListRentalPoliciesInputSchema = z.object({})
export type ListRentalPoliciesInput = z.infer<typeof ListRentalPoliciesInputSchema>

export const ListRentalPoliciesResponseSchema = ProvenanceMetaSchema.extend({
  policies: z.array(RentalPolicySchema)
})

export type ListRentalPoliciesResponse = z.infer<typeof ListRentalPoliciesResponseSchema>

export const TeamRolesResponseSchema = ProvenanceMetaSchema.extend({
  roles: z.array(z.object({
    role_name: z.string(),
    description: z.string(),
    permissions: z.array(z.string()),
    assigned_users_count: z.number()
  })),
  service_accounts: z.array(z.object({
    account_name: z.string(),
    role: z.string(),
    api_key_masked: z.string(),
    last_active: z.string()
  }))
})

export type TeamRolesResponse = z.infer<typeof TeamRolesResponseSchema>

export const GetTeamRolesInputSchema = z.object({})
export type GetTeamRolesInput = z.infer<typeof GetTeamRolesInputSchema>

export const MigrationBatchSchema = ProvenanceMetaSchema.extend({
  batch_id: z.string(),
  legacy_system: z.enum(['Current-RMS', 'RentalDesk', 'Flex-Rentals', 'Excel-Legacy']),
  started_at: z.string(),
  total_records: z.number(),
  imported_records: z.number(),
  quarantined_records: z.number(),
  status: z.enum(['draft', 'validating', 'quarantined', 'imported', 'rolled_back']),
  quarantine_reasons: z.array(z.object({
    record_ref: z.string(),
    reason: z.string()
  })).optional()
})

export type MigrationBatch = z.infer<typeof MigrationBatchSchema>

export const ListMigrationBatchesInputSchema = z.object({})
export type ListMigrationBatchesInput = z.infer<typeof ListMigrationBatchesInputSchema>

export const MigrationBatchesResponseSchema = ProvenanceMetaSchema.extend({
  batches: z.array(MigrationBatchSchema)
})

export type MigrationBatchesResponse = z.infer<typeof MigrationBatchesResponseSchema>

export const ListAuditEventsInputSchema = z.object({
  entity_type: z.string().optional(),
  entity_id: z.string().optional(),
  actor_id: z.string().optional(),
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20)
})

export type ListAuditEventsInput = z.infer<typeof ListAuditEventsInputSchema>

export const AuditEventSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  actor: z.object({
    actor_type: z.enum(['Human', 'Agent', 'System']),
    actor_id: z.string(),
    actor_name: z.string().optional(),
    ip_address: z.string().optional()
  }),
  action: z.string(),
  entity_type: z.string(),
  entity_id: z.string(),
  request_id: z.string(),
  policy_execution: z.object({
    policy_name: z.string(),
    policy_version: z.string(),
    passed: z.boolean(),
    rule_evaluation_summary: z.string()
  }).optional(),
  before_state: z.record(z.unknown()).optional(),
  after_state: z.record(z.unknown()).optional(),
  diff_summary: z.string().optional(),
  evidence_hash_sha256: z.string().optional()
})

export type AuditEvent = z.infer<typeof AuditEventSchema>

export const ListAuditEventsResponseSchema = ProvenanceMetaSchema.extend({
  events: z.array(AuditEventSchema),
  total_count: z.number()
})

export type ListAuditEventsResponse = z.infer<typeof ListAuditEventsResponseSchema>

export const CreateUploadIntentInputSchema = z.object({
  file_name: z.string(),
  file_size_bytes: z.number(),
  mime_type: z.string(),
  purpose: z.enum(['damage_photo', 'contract_signature', 'insurance_certificate', 'legacy_import'])
})

export type CreateUploadIntentInput = z.infer<typeof CreateUploadIntentInputSchema>

export const UploadIntentResponseSchema = ProvenanceMetaSchema.extend({
  upload_intent_id: z.string(),
  upload_url: z.string(),
  expires_at: z.string(),
  expected_hash_algorithm: z.literal('SHA-256')
})

export type UploadIntentResponse = z.infer<typeof UploadIntentResponseSchema>

export const RegisterEvidenceInputSchema = z.object({
  upload_intent_id: z.string(),
  entity_doctype: z.string(),
  entity_name: z.string(),
  file_sha256: z.string()
})

export type RegisterEvidenceInput = z.infer<typeof RegisterEvidenceInputSchema>
