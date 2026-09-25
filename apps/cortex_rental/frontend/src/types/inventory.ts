import type { ProvenanceMeta } from './common'

export type SerialStatus = 'Available' | 'Reserved' | 'Checked Out' | 'Quarantine' | 'Repair' | 'Missing' | 'Decommissioned'

export interface SerialNumberItem extends ProvenanceMeta {
  serial_number: string
  item_code: string
  item_name: string
  status: SerialStatus
  current_location: string
  warehouse: string
  is_consigned: boolean
  owner_id?: string
  owner_name?: string
  consignment_rate?: number
  last_maintenance_date?: string
  next_maintenance_date?: string
}

export interface EquipmentItem extends ProvenanceMeta {
  item_code: string
  item_name: string
  category: string
  brand: string
  daily_rate: number
  weekly_rate: number
  monthly_rate: number
  currency: 'CAD'
  is_serialized: boolean
  total_fleet_quantity: number
  available_quantity: number
  maintenance_quantity: number
  rented_quantity: number
  required_accessories: string[]
  optional_accessories: string[]
  image_url?: string
}

export interface KitPackage extends ProvenanceMeta {
  kit_code: string
  kit_name: string
  category: string
  bundle_daily_rate: number
  components: Array<{
    item_code: string
    item_name: string
    quantity: number
    is_mandatory: boolean
  }>
}
