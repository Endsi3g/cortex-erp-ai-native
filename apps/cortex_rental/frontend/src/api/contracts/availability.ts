import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const AvailabilityMatrixInputSchema = z.object({
  start_date: z.string(),
  end_date: z.string(),
  view_mode: z.enum(['day', 'week', 'month']).default('week'),
  category: z.string().optional(),
  search: z.string().optional()
})

export type AvailabilityMatrixInput = z.input<typeof AvailabilityMatrixInputSchema>

export const AvailabilityBlockSchema = z.object({
  id: z.string(),
  rental_id: z.string(),
  rental_name: z.string(),
  customer_name: z.string(),
  state: z.enum(['Draft', 'Quote', 'Reservation', 'Contract', 'Checked Out', 'Maintenance', 'Quarantine']),
  start_date: z.string(),
  end_date: z.string(),
  is_conflict: z.boolean(),
  conflict_reason: z.string().optional()
})

export type AvailabilityBlock = z.infer<typeof AvailabilityBlockSchema>

export const MatrixEquipmentRowSchema = z.object({
  item_code: z.string(),
  item_name: z.string(),
  category: z.string(),
  total_fleet: z.number(),
  is_serialized: z.boolean(),
  serials: z.array(z.object({
    serial_number: stringSchema(),
    status: z.string(),
    blocks: z.array(AvailabilityBlockSchema)
  })).optional(),
  blocks: z.array(AvailabilityBlockSchema).optional()
})

function stringSchema() {
  return z.string()
}

export type MatrixEquipmentRow = z.infer<typeof MatrixEquipmentRowSchema>

export const AvailabilityMatrixResponseSchema = ProvenanceMetaSchema.extend({
  start_date: z.string(),
  end_date: z.string(),
  rows: z.array(MatrixEquipmentRowSchema)
})

export type AvailabilityMatrixResponse = z.infer<typeof AvailabilityMatrixResponseSchema>

export const AvailabilityCheckInputSchema = z.object({
  items: z.array(z.object({
    item_code: z.string(),
    quantity: z.number()
  })),
  starts_at: z.string(),
  ends_at: z.string()
})

export type AvailabilityCheckInput = z.infer<typeof AvailabilityCheckInputSchema>

export const AvailabilityCheckItemResultSchema = z.object({
  item_code: z.string(),
  requested_quantity: z.number(),
  available_quantity: z.number(),
  is_available: z.boolean(),
  conflicting_rentals: z.array(z.object({
    rental_id: z.string(),
    starts_at: z.string(),
    ends_at: z.string()
  })).optional()
})

export const AvailabilityCheckResponseSchema = ProvenanceMetaSchema.extend({
  all_available: z.boolean(),
  items: z.array(AvailabilityCheckItemResultSchema)
})

export type AvailabilityCheckResponse = z.infer<typeof AvailabilityCheckResponseSchema>

export const AlternativesInputSchema = z.object({
  item_code: z.string(),
  starts_at: z.string(),
  ends_at: z.string()
})

export type AlternativesInput = z.infer<typeof AlternativesInputSchema>

export const AlternativesResponseSchema = ProvenanceMetaSchema.extend({
  item_code: z.string(),
  alternatives: z.array(z.object({
    item_code: z.string(),
    item_name: z.string(),
    daily_rate: z.number(),
    available_quantity: z.number(),
    match_score: z.number(),
    specification_diff: z.string()
  }))
})

export type AlternativesResponse = z.infer<typeof AlternativesResponseSchema>
