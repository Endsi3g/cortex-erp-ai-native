import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

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
