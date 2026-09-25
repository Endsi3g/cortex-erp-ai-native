import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const RentalCustomerOptionSchema = z.object({
  id: z.string(),
  name: z.string(),
  insurance_valid: z.boolean().nullable(),
})
export type RentalCustomerOption = z.infer<typeof RentalCustomerOptionSchema>

export const RentalCatalogOptionSchema = z.object({
  item_code: z.string(),
  item_name: z.string(),
  category: z.string(),
  daily_rate: z.number(),
  is_serialized: z.boolean(),
  required_accessories: z.array(z.string()).default([]),
})
export type RentalCatalogOption = z.infer<typeof RentalCatalogOptionSchema>

/** Mirrors TransactionStateService.VALID_TRANSITIONS on the server. */
export const RentalStateSchema = z.enum([
  'Quote',
  'Reservation',
  'Contract',
  'Checked Out',
  'Returned',
  'Closed',
  'Cancelled',
  'Disputed',
  'Quarantine'
])
export type RentalStateValue = z.infer<typeof RentalStateSchema>

export const RentalActionSchema = z.enum([
  'edit_quote', 'confirm_reservation', 'request_contract', 'record_advance', 'checkout', 'checkin',
  'prepare_final_invoice', 'close', 'cancel', 'verify_readiness'
])
export type RentalAction = z.infer<typeof RentalActionSchema>

export const RentalLineItemSchema = z.object({
  id: z.string(),
  item_code: z.string(),
  item_name: z.string(),
  category: z.string(),
  quantity: z.number(),
  daily_rate: z.number(),
  discount_percentage: z.number().default(0),
  kit: z.string().nullable().optional(),
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
  currency: z.string().nullable(),
  readiness: RentalReadinessSchema,
  items: z.array(RentalLineItemSchema),
  notes: z.string().optional(),
  erpnext_sales_order: z.string().nullable().optional(),
  final_invoice: z.string().nullable().optional(),
  advance_amount: z.number().optional(),
  available_actions: z.array(RentalActionSchema).default([]),
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
    discount_percentage: z.number().optional(),
    kit: z.string().optional()
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
  tax_lines: z.array(z.object({ description: z.string(), rate: z.number(), amount: z.number() })).default([]),
  tax_template: z.string().nullable().optional(),
  tax_estimate_complete: z.boolean().optional(),
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
    discount_percentage: z.number().optional(),
    kit: z.string().optional()
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
    discount_percentage: z.number().optional(),
    kit: z.string().optional()
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

/** Lightweight list row (cortex_rental.api.v1.rentals.list_rental_summaries). */
export interface RentalSummary extends Record<string, unknown> {
  name: string
  customer: string
  customer_name: string
  project_name: string
  rental_state: RentalStateValue
  starts_at: string
  ends_at: string
  billable_days: number
  grand_total: number
  currency: string | null
  ready: boolean
}

export interface ListRentalSummariesInput {
  page: number
  page_size: number
  state?: RentalStateValue
  search?: string
  starts_from?: string
  starts_to?: string
}

export type ReadinessField = 'customer_account_ready' | 'insurance_ready'

export interface OperationsRow {
  name: string
  customer: string
  customer_name: string
  project_name: string
  rental_state: RentalStateValue
  starts_at: string
  ends_at: string
  missing_requirements: Array<'customer_account_ready' | 'insurance_ready' | 'payment_ready'>
}

export interface OperationsOverview {
  provenance?: 'api' | 'mock'
  day: string
  generated_at: string
  kpis: { departures: number; returns: number; overdue: number; exceptions: number; approvals_pending: number; inbound_pending: number }
  departures: OperationsRow[]
  returns: OperationsRow[]
  overdue: OperationsRow[]
  exceptions: OperationsRow[]
  at_risk: OperationsRow[]
  serials_out_of_service: Array<{ serial_no: string; item_code: string; status: string }>
}
