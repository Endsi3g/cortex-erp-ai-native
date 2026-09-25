import type { ProvenanceMeta } from './common'

import type { RentalAction, RentalStateValue } from '@/api/contracts/rentals'

/** Single source of truth: the server state machine (see api/contracts/rentals.ts). */
export type RentalState = RentalStateValue

export interface RentalReadiness {
  customer_account_ready: boolean
  insurance_ready: boolean
  payment_ready: boolean
  overall_ready: boolean
  missing_requirements: string[]
}

export interface RentalLineItem {
  id: string
  item_code: string
  item_name: string
  category: string
  quantity: number
  daily_rate: number
  discount_percentage: number
  billable_days: number
  subtotal: number
  assigned_serials: string[]
  scanned_checkout_serials: string[]
  scanned_checkin_serials: string[]
  is_consigned: boolean
  owner_code?: string
}

export interface RentalTransaction extends ProvenanceMeta {
  id: string
  name: string
  company: string
  customer_id: string
  customer_name: string
  customer_contact_email?: string
  project_name?: string
  rental_state: RentalState
  starts_at: string
  ends_at: string
  calendar_days: number
  billable_days: number
  subtotal: number
  discount_total?: number
  tax_rate: number
  tax_amount: number
  grand_total: number
  currency: string | null
  readiness: RentalReadiness
  items: RentalLineItem[]
  notes?: string
  erpnext_sales_order?: string | null
  final_invoice?: string | null
  advance_amount?: number
  available_actions: RentalAction[]
  created_at: string
  updated_at: string
  version: number
}
