import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

/** One owner as listed on the consignment dashboard (cortex_rental.api.v1.consignment). */
export type StatementStatus = 'not_prepared' | 'draft' | 'approved' | 'paid'

export interface ConsignmentOwner extends Record<string, unknown> {
  id: string
  owner_code: string
  display_name: string
  owner_type: 'House' | 'Third-Party' | 'Co-Investment'
  contact_email: string
  contact_phone: string
  default_commission_percentage: number
  active_serials_count: number
  period_revenue: number
  period_amount_due: number
  statement_status: StatementStatus
}

export interface ConsignmentOwnerRecord extends ConsignmentOwner {
  billing_address: string
  serials: Array<{ serial_no: string; item_code: string; status: string }>
  statements: Array<{ period: string; status: string; amount: number }>
  can_manage: boolean
}

export interface ListOwnersInput {
  search?: string
  period?: string
}

export interface ListOwnersResponse {
  provenance?: 'api' | 'mock'
  items: ConsignmentOwner[]
  total_count: number
}

export interface ConsignmentDashboardInput {
  period?: string // "2026-09"
}

export interface ConsignmentDashboardResponse {
  provenance?: 'api' | 'mock'
  period: string
  currency: string | null
  current_month_total_payout: number
  previous_month_total_payout: number
  active_owners_count: number
  active_consigned_serials_count: number
  owners: ConsignmentOwner[]
  top_earning_items: Array<{ serial_number: string; item_name: string; owner_code: string; revenue_generated: number; owner_payout: number }>
}

export type OwnerDraft = Partial<Pick<ConsignmentOwnerRecord, 'id' | 'owner_code' | 'display_name' | 'owner_type' | 'contact_email' | 'contact_phone' | 'default_commission_percentage' | 'billing_address'>>

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
  currency: z.string(),
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

export const OwnerStatementResponseSchema = ProvenanceMetaSchema.partial().extend({
  statement: OwnerStatementSafeSchema,
  status: z.enum(['not_prepared', 'draft', 'approved', 'paid']).optional()
})

export type OwnerStatementResponse = z.infer<typeof OwnerStatementResponseSchema>

