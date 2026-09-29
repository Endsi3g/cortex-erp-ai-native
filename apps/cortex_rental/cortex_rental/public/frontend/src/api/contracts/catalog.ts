import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const EquipmentItemSchema = ProvenanceMetaSchema.extend({
  item_code: z.string(),
  item_name: z.string(),
  category: z.string(),
  // Not held by the ERP for every item: absent means "non fourni", never an estimate.
  brand: z.string().optional(),
  daily_rate: z.number(),
  weekly_rate: z.number().optional(),
  monthly_rate: z.number().optional(),
  currency: z.string(),
  is_serialized: z.boolean(),
  total_fleet_quantity: z.number(),
  available_quantity: z.number(),
  maintenance_quantity: z.number(),
  rented_quantity: z.number(),
  required_accessories: z.array(z.string()),
  optional_accessories: z.array(z.string()).optional(),
  image_url: z.string().optional(),
  serials: z.array(z.object({
    serial_number: z.string(),
    status: z.enum(['Available', 'Reserved', 'Checked Out', 'Quarantine', 'Repair', 'Missing', 'Decommissioned']),
    warehouse: z.string().optional()
  })).optional()
})

export type EquipmentItem = z.infer<typeof EquipmentItemSchema>

export const SerialNumberItemSchema = ProvenanceMetaSchema.extend({
  serial_number: z.string(),
  item_code: z.string(),
  item_name: z.string(),
  status: z.enum(['Available', 'Reserved', 'Checked Out', 'Quarantine', 'Repair', 'Missing', 'Decommissioned']),
  current_location: z.string().optional(),
  warehouse: z.string().optional(),
  is_consigned: z.boolean(),
  owner_id: z.string().optional(),
  owner_name: z.string().optional(),
  consignment_rate: z.number().optional(),
  last_maintenance_date: z.string().optional(),
  next_maintenance_date: z.string().optional()
})

export type SerialNumberItem = z.infer<typeof SerialNumberItemSchema>

export const KitPackageSchema = ProvenanceMetaSchema.extend({
  kit_code: z.string(),
  kit_name: z.string(),
  category: z.string(),
  bundle_daily_rate: z.number().optional(),
  components: z.array(z.object({
    item_code: z.string(),
    item_name: z.string(),
    quantity: z.number(),
    is_mandatory: z.boolean().optional()
  }))
})

export type KitPackage = z.infer<typeof KitPackageSchema>

export const ListEquipmentInputSchema = z.object({
  category: z.string().optional(),
  search: z.string().optional(),
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20)
})

export type ListEquipmentInput = z.infer<typeof ListEquipmentInputSchema>

export const ListEquipmentResponseSchema = ProvenanceMetaSchema.extend({
  items: z.array(EquipmentItemSchema),
  total_count: z.number()
})

export type ListEquipmentResponse = z.infer<typeof ListEquipmentResponseSchema>

export const GetEquipmentInputSchema = z.object({
  item_code: z.string()
})

export type GetEquipmentInput = z.infer<typeof GetEquipmentInputSchema>

export const GetEquipmentResponseSchema = EquipmentItemSchema
export type GetEquipmentResponse = z.infer<typeof GetEquipmentResponseSchema>

export const GetSerialInputSchema = z.object({
  serial_number: z.string()
})

export type GetSerialInput = z.infer<typeof GetSerialInputSchema>

export const GetSerialResponseSchema = SerialNumberItemSchema
export type GetSerialResponse = z.infer<typeof GetSerialResponseSchema>

export const ListKitsInputSchema = z.object({
  category: z.string().optional()
})

export type ListKitsInput = z.infer<typeof ListKitsInputSchema>

export const ListKitsResponseSchema = ProvenanceMetaSchema.extend({
  kits: z.array(KitPackageSchema),
  total_count: z.number()
})

export type ListKitsResponse = z.infer<typeof ListKitsResponseSchema>
