import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const StartCheckoutInputSchema = z.object({
  rental_id: z.string()
})

export type StartCheckoutInput = z.infer<typeof StartCheckoutInputSchema>

export const ScanCheckoutSerialInputSchema = z.object({
  rental_id: z.string(),
  serial_number: z.string()
})

export type ScanCheckoutSerialInput = z.infer<typeof ScanCheckoutSerialInputSchema>

export const CompleteCheckoutInputSchema = z.object({
  rental_id: z.string(),
  signature_name: z.string().optional()
})

export type CompleteCheckoutInput = z.infer<typeof CompleteCheckoutInputSchema>

export const StartCheckinInputSchema = z.object({
  rental_id: z.string()
})

export type StartCheckinInput = z.infer<typeof StartCheckinInputSchema>

export const ScanCheckinSerialInputSchema = z.object({
  rental_id: z.string(),
  serial_number: z.string(),
  condition: z.enum(['Good', 'Damaged', 'Missing_Accessory', 'Needs_Clean']).default('Good')
})

export type ScanCheckinSerialInput = z.infer<typeof ScanCheckinSerialInputSchema>

export const MarkSerialMissingInputSchema = z.object({
  rental_id: z.string(),
  serial_number: z.string(),
  reason: z.string()
})

export type MarkSerialMissingInput = z.infer<typeof MarkSerialMissingInputSchema>

export const AddDamageEvidenceInputSchema = z.object({
  rental_id: z.string(),
  serial_number: z.string(),
  description: z.string(),
  photo_upload_id: z.string().optional(),
  severity: z.enum(['minor', 'major', 'unusable'])
})

export type AddDamageEvidenceInput = z.infer<typeof AddDamageEvidenceInputSchema>

export const CompletePartialReturnInputSchema = z.object({
  rental_id: z.string(),
  notes: z.string().optional(),
  finalize_mode: z.enum(['auto', 'partial', 'full', 'settle_with_loss']).default('auto'),
  items: z.array(z.object({
    transaction_item: z.string(),
    item_code: z.string(),
    serial_no: z.string().optional(),
    expected_qty: z.number(),
    returned_qty: z.number(),
    condition: z.enum(['Good', 'Damaged', 'Missing_Accessory', 'Needs_Clean']).default('Good'),
    disposition: z.enum(['Return to Stock', 'Quarantine', 'Repair', 'Missing', 'Write-off']).default('Return to Stock'),
    damage_severity: z.enum(['None', 'Cosmetic', 'Functional', 'Blocking']).default('None'),
    notes: z.string().optional(),
    file_name: z.string().optional()
  })).optional()
})

export type CompletePartialReturnInput = z.input<typeof CompletePartialReturnInputSchema>

export const LookupScanInputSchema = z.object({
  barcode: z.string()
})

export type LookupScanInput = z.infer<typeof LookupScanInputSchema>

export const LookupScanResponseSchema = ProvenanceMetaSchema.extend({
  barcode: z.string(),
  entity_type: z.enum(['serial_number', 'item', 'rental', 'unknown']),
  entity_id: z.string().optional(),
  display_title: z.string(),
  current_status: z.string(),
  associated_rental_id: z.string().optional()
})

export type LookupScanResponse = z.infer<typeof LookupScanResponseSchema>
