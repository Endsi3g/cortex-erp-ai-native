/** Customers for staff — cortex_rental.api.v1.clients (ERPNext Customer scoped by cortex_company). */

export type InsuranceStatus = 'valid' | 'expired' | 'unknown'

export interface CustomerRow extends Record<string, unknown> {
  name: string
  customer_name: string
  customer_group: string
  email: string
  phone: string
  rentals: number
  active_rentals: number
  outstanding: number
  insurance_status: InsuranceStatus
  insurance_valid_until: string | null
}

export interface ListCustomersInput {
  search?: string
  page: number
  page_size: number
}

export interface ListCustomersResponse {
  provenance?: 'api' | 'mock'
  items: CustomerRow[]
  total_count: number
  page: number
  page_size: number
  currency: string | null
}

export interface CustomerRecord {
  provenance?: 'api' | 'mock'
  name: string
  customer_name: string
  customer_type: string
  customer_group: string
  email: string
  phone: string
  insurance: { valid_until: string | null; status: InsuranceStatus }
  currency: string | null
  stats: { rentals: number; active_rentals: number; lifetime_value: number; outstanding: number; disputes: number }
  rentals: Array<{ name: string; project_name: string; rental_state: string; starts_at: string; ends_at: string; grand_total: number }>
  invoices: Array<{ name: string; posting_date: string; status: string; docstatus: number; grand_total: number; outstanding_amount: number; rental: string | null }>
  payments: Array<{ name: string; posting_date: string; docstatus: number; paid_amount: number; mode_of_payment: string | null; rental: string | null }>
  can_verify: boolean
}

export interface NewCustomerInput {
  customer_name: string
  customer_type: 'Company' | 'Individual'
  email?: string
  phone?: string
}
