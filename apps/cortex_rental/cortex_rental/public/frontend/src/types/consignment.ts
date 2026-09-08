import type { ProvenanceMeta } from './common'

export interface ConsignmentOwner extends ProvenanceMeta {
  id: string
  owner_code: string
  display_name: string
  company_name?: string
  contact_email: string
  contact_phone?: string
  default_commission_percentage: number // e.g. 70 means 70% to owner, 30% to rental house
  active_serials_count: number
  pending_payout_amount: number
  currency: 'CAD'
}

export interface OwnerStatementLineSafe {
  serial_number: string
  equipment_name: string
  rental_start_date: string
  rental_end_date: string
  billable_days: number
  rate: number
  discount_amount: number
  consignment_percentage: number
  owner_amount: number
  invoice_reference: string
}

export interface OwnerStatementSafe {
  owner: {
    id: string
    display_name: string
    code: string
  }
  period: {
    start: string
    end: string
    timezone: string
  }
  currency: 'CAD'
  totals: {
    eligible_net_revenue: number
    owner_amount_due: number
  }
  lines: OwnerStatementLineSafe[]
  generated_at: string
  snapshot_version: string
}

export interface ConsignmentDashboardData extends ProvenanceMeta {
  current_month_total_payout: number
  previous_month_total_payout: number
  active_owners_count: number
  active_consigned_serials_count: number
  top_earning_items: Array<{
    item_code: string
    item_name: string
    owner_code: string
    revenue_generated: number
    owner_payout: number
  }>
  pending_statements: Array<{
    owner_id: string
    owner_name: string
    period: string
    amount_due: number
    status: 'draft' | 'approved' | 'paid'
  }>
}
