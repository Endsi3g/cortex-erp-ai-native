import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const ConsignmentOwnerSchema = ProvenanceMetaSchema.extend({
  id: z.string(),
  owner_code: z.string(),
  display_name: z.string(),
  company_name: z.string().optional(),
  contact_email: z.string(),
  contact_phone: z.string().optional(),
  default_commission_percentage: z.number(),
  active_serials_count: z.number(),
  pending_payout_amount: z.number(),
  currency: z.literal('CAD')
})

export type ConsignmentOwner = z.infer<typeof ConsignmentOwnerSchema>

export const ListOwnersInputSchema = z.object({
  search: z.string().optional(),
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20)
})

export type ListOwnersInput = z.input<typeof ListOwnersInputSchema>

export const ListOwnersResponseSchema = ProvenanceMetaSchema.extend({
  items: z.array(ConsignmentOwnerSchema),
  total_count: z.number()
})

export type ListOwnersResponse = z.infer<typeof ListOwnersResponseSchema>

export const ConsignmentDashboardInputSchema = z.object({
  period: z.string().optional() // e.g. "2026-09"
})

export type ConsignmentDashboardInput = z.infer<typeof ConsignmentDashboardInputSchema>

export const ConsignmentDashboardResponseSchema = ProvenanceMetaSchema.extend({
  current_month_total_payout: z.number(),
  previous_month_total_payout: z.number(),
  active_owners_count: z.number(),
  active_consigned_serials_count: z.number(),
  top_earning_items: z.array(z.object({
    item_code: z.string(),
    item_name: z.string(),
    owner_code: z.string(),
    revenue_generated: z.number(),
    owner_payout: z.number()
  })),
  pending_statements: z.array(z.object({
    owner_id: z.string(),
    owner_name: z.string(),
    period: z.string(),
    amount_due: z.number(),
    status: z.enum(['draft', 'approved', 'paid'])
  }))
})

export type ConsignmentDashboardResponse = z.infer<typeof ConsignmentDashboardResponseSchema>

export const OwnerStatementLineSafeSchema = z.object({
  serial_number: z.string(),
  equipment_name: z.string(),
  rental_start_date: z.string(),
  rental_end_date: z.string(),
  billable_days: z.number(),
  rate: z.number(),
  discount_amount: z.number(),
  consignment_percentage: z.number(),
  owner_amount: z.number(),
  invoice_reference: z.string()
}).strict()

export const OwnerStatementSafeSchema = z.object({
  owner: z.object({
    id: z.string(),
    display_name: z.string(),
    code: z.string()
  }).strict(),
  period: z.object({
    start: z.string(),
    end: z.string(),
    timezone: z.string()
  }).strict(),
  currency: z.literal('CAD'),
  totals: z.object({
    eligible_net_revenue: z.number(),
    owner_amount_due: z.number()
  }).strict(),
  lines: z.array(OwnerStatementLineSafeSchema),
  generated_at: z.string(),
  snapshot_version: z.string()
}).strict()

export type OwnerStatementSafe = z.infer<typeof OwnerStatementSafeSchema>

export const OwnerStatementInputSchema = z.object({
  owner_id: z.string(),
  period: z.string()
})

export type OwnerStatementInput = z.infer<typeof OwnerStatementInputSchema>

export const OwnerStatementResponseSchema = ProvenanceMetaSchema.extend({
  statement: OwnerStatementSafeSchema
})

export type OwnerStatementResponse = z.infer<typeof OwnerStatementResponseSchema>

export const OwnerStatementExportInputSchema = z.object({
  owner_id: z.string(),
  period: z.string(),
  format: z.enum(['pdf', 'csv'])
})

export type OwnerStatementExportInput = z.infer<typeof OwnerStatementExportInputSchema>
