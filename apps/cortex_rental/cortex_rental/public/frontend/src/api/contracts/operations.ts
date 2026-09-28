import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const OperationsCountsSchema = z.object({
  departures_today: z.number(),
  returns_due_today: z.number(),
  overdue_returns: z.number(),
  disputed_or_quarantined: z.number(),
  missing_serials: z.number(),
  inbound_to_review: z.number(),
  exceptions: z.number(),
  // null = the caller's role cannot decide approvals, so the count is not exposed.
  pending_approvals: z.number().nullable()
})

export const OperationsTimelineEntrySchema = z.object({
  kind: z.enum(['departure', 'return']),
  rental_id: z.string(),
  customer: z.string(),
  state: z.string(),
  at: z.string()
})

export const OperationsOverviewResponseSchema = ProvenanceMetaSchema.extend({
  counts: OperationsCountsSchema,
  timeline: z.array(OperationsTimelineEntrySchema),
  as_of: z.string()
})

export type OperationsCounts = z.infer<typeof OperationsCountsSchema>
export type OperationsTimelineEntry = z.infer<typeof OperationsTimelineEntrySchema>
export type OperationsOverviewResponse = z.infer<typeof OperationsOverviewResponseSchema>
