import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const RentalStateSchema = z.enum([
  'Draft',
  'Quote',
  'Reservation',
  'Contract',
  'Checked Out',
  'Partially Returned',
  'Returned',
  'Invoiced',
  'Cancelled'
])

export const RentalLineItemSchema = z.object({
  id: z.string(),
  item_code: z.string(),
  item_name: z.string(),
  category: z.string(),
  quantity: z.number(),
  daily_rate: z.number(),
  discount_percentage: z.number().default(0),
  billable_days: z.number(),
  subtotal: z.number(),
  assigned_serials: z.array(z.string()).default([]),
  scanned_checkout_serials: z.array(z.string()).default([]),
  scanned_checkin_serials: z.array(z.string()).default([]),
  is_consigned: z.boolean().default(false),
  owner_code: z.string().optional()
})

export type RentalLineItem = z.infer<typeof RentalLineItemSchema>

export const RentalReadinessSchema = z.object({
  customer_account_ready: z.boolean(),
  insurance_ready: z.boolean(),
  payment_ready: z.boolean(),
  overall_ready: z.boolean(),
  missing_requirements: z.array(z.string())
})

export const RentalTransactionSchema = ProvenanceMetaSchema.extend({
  id: z.string(),
  name: z.string(),
  company: z.string(),
  customer_id: z.string(),
  customer_name: z.string(),
  customer_contact_email: z.string().optional(),
  project_name: z.string().optional(),
  rental_state: RentalStateSchema,
  starts_at: z.string(),
  ends_at: z.string(),
  calendar_days: z.number(),
  billable_days: z.number(),
  subtotal: z.number(),
  discount_total: z.number().optional(),
  tax_rate: z.number(),
  tax_amount: z.number(),
  grand_total: z.number(),
  currency: z.literal('CAD'),
  readiness: RentalReadinessSchema,
  items: z.array(RentalLineItemSchema),
  notes: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  version: z.number()
})

export type RentalTransaction = z.infer<typeof RentalTransactionSchema>

export const ListRentalsInputSchema = z.object({
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20),
  state: RentalStateSchema.optional(),
  customer_id: z.string().optional(),
  search: z.string().optional(),
  starts_after: z.string().optional(),
  ends_before: z.string().optional()
})

export type ListRentalsInput = z.infer<typeof ListRentalsInputSchema>

export const ListRentalsResponseSchema = ProvenanceMetaSchema.extend({
  items: z.array(RentalTransactionSchema),
  total_count: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number()
})

export type ListRentalsResponse = z.infer<typeof ListRentalsResponseSchema>

export const GetRentalInputSchema = z.object({
  id: z.string()
})

export type GetRentalInput = z.infer<typeof GetRentalInputSchema>

export const GetRentalResponseSchema = RentalTransactionSchema
export type GetRentalResponse = z.infer<typeof GetRentalResponseSchema>

export const PreviewPricingInputSchema = z.object({
  items: z.array(z.object({
    item_code: z.string(),
    quantity: z.number(),
    daily_rate: z.number().optional(),
    discount_percentage: z.number().optional()
  })),
  starts_at: z.string(),
  ends_at: z.string(),
  customer_id: z.string().optional()
})

export type PreviewPricingInput = z.infer<typeof PreviewPricingInputSchema>

export const PreviewPricingResponseSchema = ProvenanceMetaSchema.extend({
  calendar_days: z.number(),
  billable_days: z.number(),
  subtotal: z.number(),
  discount_amount: z.number(),
  tax_amount: z.number(),
  grand_total: z.number(),
  pricing_rule_applied: z.string(),
  lines: z.array(z.object({
    item_code: z.string(),
    daily_rate: z.number(),
    billable_days: z.number(),
    line_subtotal: z.number()
  }))
})

export type PreviewPricingResponse = z.infer<typeof PreviewPricingResponseSchema>

export const CreateQuoteDraftInputSchema = z.object({
  customer_id: z.string(),
  starts_at: z.string(),
  ends_at: z.string(),
  project_name: z.string().optional(),
  notes: z.string().optional(),
  items: z.array(z.object({
    item_code: z.string(),
    quantity: z.number(),
    discount_percentage: z.number().optional()
  }))
})

export type CreateQuoteDraftInput = z.infer<typeof CreateQuoteDraftInputSchema>

export const UpdateQuoteDraftInputSchema = z.object({
  rental_id: z.string(),
  starts_at: z.string().optional(),
  ends_at: z.string().optional(),
  project_name: z.string().optional(),
  notes: z.string().optional(),
  items: z.array(z.object({
    item_code: z.string(),
    quantity: z.number(),
    discount_percentage: z.number().optional()
  })).optional(),
  version: z.number()
})

export type UpdateQuoteDraftInput = z.infer<typeof UpdateQuoteDraftInputSchema>

export const RequestReservationInputSchema = z.object({
  rental_id: z.string(),
  version: z.number()
})

export type RequestReservationInput = z.infer<typeof RequestReservationInputSchema>

export const RequestContractApprovalInputSchema = z.object({
  rental_id: z.string(),
  version: z.number(),
  override_reason: z.string().optional()
})

export type RequestContractApprovalInput = z.infer<typeof RequestContractApprovalInputSchema>

export const GetRentalAuditInputSchema = z.object({
  rental_id: z.string()
})

export type GetRentalAuditInput = z.infer<typeof GetRentalAuditInputSchema>

export const GetRentalAuditResponseSchema = ProvenanceMetaSchema.extend({
  rental_id: z.string(),
  events: z.array(z.object({
    id: z.string(),
    timestamp: z.string(),
    actor: z.object({
      actor_type: z.enum(['Human', 'Agent', 'System']),
      actor_id: z.string()
    }),
    action: z.string(),
    diff_summary: z.string().optional()
  }))
})

export type GetRentalAuditResponse = z.infer<typeof GetRentalAuditResponseSchema>
