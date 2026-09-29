import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const CustomerSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  customer_group: z.string().optional(),
  territory: z.string().optional(),
  insurance_valid_until: z.string().optional(),
  rentals_count: z.number(),
  open_rentals_count: z.number(),
  billed_total: z.number(),
  last_rental_start: z.string().optional()
})
export type CustomerSummary = z.infer<typeof CustomerSummarySchema>

export const ListCustomersInputSchema = z.object({
  search: z.string().optional(),
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20)
})
export type ListCustomersInput = z.input<typeof ListCustomersInputSchema>

export const ListCustomersResponseSchema = ProvenanceMetaSchema.extend({
  items: z.array(CustomerSummarySchema),
  total_count: z.number()
})
export type ListCustomersResponse = z.infer<typeof ListCustomersResponseSchema>

export interface PnlAccountNode {
  id: string
  name: string
  depth: number
  type: 'group' | 'account'
  total?: number | null
  values: Record<string, number | null | undefined>
  children: PnlAccountNode[]
}

export const PnlAccountNodeSchema: z.ZodType<PnlAccountNode> = z.lazy(() =>
  z.object({
    id: z.string(),
    name: z.string(),
    depth: z.number(),
    type: z.enum(['group', 'account']),
    total: z.number().nullable().optional(),
    values: z.record(z.number().nullable().optional()),
    children: z.array(PnlAccountNodeSchema)
  })
)

export const ProfitAndLossInputSchema = z.object({
  fiscal_year: z.string().optional(),
  from_date: z.string().optional(),
  to_date: z.string().optional(),
  periodicity: z.enum(['Monthly', 'Quarterly', 'Half-Yearly', 'Yearly']).optional(),
  accumulated_values: z.boolean().optional()
})
export type ProfitAndLossInput = z.infer<typeof ProfitAndLossInputSchema>

// The endpoint returns its report inside the standard `data` envelope without the provenance fields.
export const ProfitAndLossResponseSchema = z.object({
  provenance: z.enum(['api', 'mock', 'demo', 'stale']).optional(),
  last_synced_at: z.string().optional(),
  company: z.string().optional(),
  fiscalYear: z.string().nullable().optional(),
  totalIncome: z.number(),
  totalExpense: z.number(),
  netProfit: z.number(),
  periods: z.array(z.object({ key: z.string(), label: z.string(), income: z.number(), expense: z.number(), profitLoss: z.number() })),
  accounts: z.array(PnlAccountNodeSchema),
  reportError: z.string().optional()
})
export type ProfitAndLossResponse = z.infer<typeof ProfitAndLossResponseSchema>
