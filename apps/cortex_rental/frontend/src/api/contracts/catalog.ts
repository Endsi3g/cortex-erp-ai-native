/**
 * Catalog contracts — cortex_rental.api.v1.catalog (rental profiles over
 * ERPNext Items, ERPNext Serial Nos with the Cortex status, Cortex kits).
 */
import type { PagedResult } from './billing'

export type SerialStatus = 'Active' | 'Quarantine' | 'Under Repair' | 'Missing' | 'Decommissioned'

export interface EquipmentRow extends Record<string, unknown> {
  item_code: string
  item_name: string
  category: string
  daily_rate: number
  replacement_value: number
  is_serialized: boolean
  currency: string | null
  fleet_total: number
  fleet_active: number
  fleet_out: number
  fleet_unavailable: number
}

export interface ListEquipmentInput {
  search?: string
  category?: string
  page: number
  page_size: number
}
export type ListEquipmentResponse = PagedResult<EquipmentRow>

export interface GetEquipmentInput {
  item_code: string
}

export interface EquipmentSerial extends Record<string, unknown> {
  serial_no: string
  status: SerialStatus
  current_rental: string | null
  warranty_expiry_date: string | null
}

export interface EquipmentRecord {
  provenance?: 'api' | 'mock'
  item_code: string
  item_name: string
  description: string
  image: string | null
  item_group: string | null
  brand: string | null
  category: string
  daily_rate: number
  replacement_value: number
  deposit_required: number
  prep_hours: number
  is_serialized: boolean
  total_quantity: number
  is_consignment_allowed: boolean
  required_accessories: string[]
  currency: string | null
  fleet: { total: number; active: number; out: number; unavailable: number; by_status?: Record<string, number> }
  serials: EquipmentSerial[]
  pricing_curve: Array<{ calendar_days: number; billable_days: number; price: number }>
  can_edit: boolean
}
export type GetEquipmentResponse = EquipmentRecord

export type EquipmentProfileChanges = Partial<Pick<EquipmentRecord, 'daily_rate' | 'replacement_value' | 'deposit_required' | 'prep_hours' | 'total_quantity' | 'category'>> & {
  required_accessories?: string
}

export interface GetSerialInput {
  serial_number: string
}

export interface SerialRecord {
  provenance?: 'api' | 'mock'
  serial_no: string
  item_code: string
  item_name: string
  erpnext_status: string | null
  status: SerialStatus
  consignment_owner?: string | null
  warranty_expiry_date: string | null
  current_rental: string | null
  rentals: Array<{ name: string; customer: string; rental_state: string; starts_at: string; ends_at: string }>
  returns: Array<{ checkin: string; transaction: string; checked_in_at: string; condition: string; disposition: string; damage_severity: string; damage_type: string; estimated_repair_cost: number; notes: string }>
  status_history: Array<{ id: string; timestamp: string; actor: string; action: string; detail: string }>
  can_change_status: boolean
}
export type GetSerialResponse = SerialRecord

export interface RentalKitItem {
  item_code: string
  item_name: string
  qty: number
  is_optional: boolean
  daily_rate: number
}

export interface RentalKit {
  name?: string
  kit_name: string
  is_active: boolean
  discount_percentage: number
  description: string
  items: RentalKitItem[]
}

export interface ListKitsInput {
  include_inactive?: boolean
}
export type ListKitsResponse = RentalKit[]
