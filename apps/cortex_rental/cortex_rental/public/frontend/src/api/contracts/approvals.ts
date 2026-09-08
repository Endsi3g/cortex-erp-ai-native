import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const ApprovalTypeSchema = z.enum([
  'Contract Confirmation',
  'Discount Override',
  'Dispute Settlement',
  'Credit Limit Increase',
  'AI Draft Execution'
])

export const ApprovalStatusSchema = z.enum(['pending', 'approved', 'rejected', 'expired'])

export const ApprovalRequestItemSchema = ProvenanceMetaSchema.extend({
  id: z.string(),
  approval_type: ApprovalTypeSchema,
  status: ApprovalStatusSchema,
  title: stringSchema(),
  description: stringSchema(),
  reference_doctype: stringSchema(),
  reference_name: stringSchema(),
  requested_by_type: z.enum(['Human', 'Agent']),
  requested_by: stringSchema(),
  threshold_exceeded_details: z.string().optional(),
  before_state: z.record(z.unknown()).optional(),
  after_state: z.record(z.unknown()).optional(),
  evidence_ids: z.array(z.string()).optional(),
  created_at: stringSchema(),
  resolved_at: z.string().optional(),
  resolved_by: z.string().optional(),
  rejection_reason: z.string().optional()
})

function stringSchema() {
  return z.string()
}

export type ApprovalRequestItem = z.infer<typeof ApprovalRequestItemSchema>

export const ListApprovalRequestsInputSchema = z.object({
  status: ApprovalStatusSchema.optional().default('pending'),
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20)
})

export type ListApprovalRequestsInput = z.input<typeof ListApprovalRequestsInputSchema>

export const ListApprovalsResponseSchema = ProvenanceMetaSchema.extend({
  items: z.array(ApprovalRequestItemSchema),
  total_count: z.number()
})

export type ListApprovalsResponse = z.infer<typeof ListApprovalsResponseSchema>

export const GetApprovalRequestInputSchema = z.object({
  id: z.string()
})

export type GetApprovalRequestInput = z.infer<typeof GetApprovalRequestInputSchema>

export const GetApprovalResponseSchema = ApprovalRequestItemSchema
export type GetApprovalResponse = z.infer<typeof GetApprovalResponseSchema>

export const ApproveApprovalInputSchema = z.object({
  id: z.string(),
  notes: z.string().optional()
})

export type ApproveApprovalInput = z.infer<typeof ApproveApprovalInputSchema>

export const RejectApprovalInputSchema = z.object({
  id: z.string(),
  reason: z.string().min(3, 'Rejection reason is mandatory')
})

export type RejectApprovalInput = z.infer<typeof RejectApprovalInputSchema>
