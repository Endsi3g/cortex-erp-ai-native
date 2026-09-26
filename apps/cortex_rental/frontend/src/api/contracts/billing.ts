/** Billing contracts — ERPNext Sales Order / Payment Entry / Sales Invoice behind a rental. */

export type InvoiceStatus = 'Draft' | 'Unpaid' | 'Partly Paid' | 'Paid' | 'Overdue' | 'Return' | 'Credit Note Issued' | 'Cancelled'

export interface InvoiceRow extends Record<string, unknown> {
  name: string
  customer: string
  customer_name: string
  posting_date: string
  due_date: string | null
  status: InvoiceStatus
  docstatus: 0 | 1 | 2
  currency: string
  grand_total: number
  total_advance: number
  outstanding_amount: number
  cortex_rental_transaction: string
  is_return: 0 | 1
}

export interface PaymentRow extends Record<string, unknown> {
  name: string
  party: string
  party_name: string
  posting_date: string
  mode_of_payment: string | null
  reference_no: string | null
  paid_amount: number
  unallocated_amount: number
  currency: string
  docstatus: 0 | 1
  cortex_rental_transaction: string
}

export interface PagedResult<T> {
  items: T[]
  total_count: number
  page: number
  page_size: number
  /** 'mock' only for the explicit demo client. */
  provenance?: 'api' | 'mock'
}

export interface ListInvoicesInput {
  status?: InvoiceStatus
  search?: string
  from_date?: string
  to_date?: string
  page: number
  page_size: number
}

export type ListPaymentsInput = Omit<ListInvoicesInput, 'status'>

export interface RentalBilling {
  currency: string | null
  sales_order: { name: string; status: string; docstatus: number; grand_total: number; advance_paid: number; per_billed: number } | null
  advance: { percentage_amount: number; guarantee_amount: number; requested: number; received: number; covered: boolean }
  payments: Array<{ name: string; docstatus: number; posting_date: string; paid_amount: number; mode_of_payment: string | null; reference_no: string | null }>
  final_invoice: { name: string; status: string; docstatus: number; grand_total: number; total_advance: number; outstanding_amount: number } | null
}

export interface PaymentMode {
  name: string
  has_account: boolean
}

export interface RecordAdvanceInput {
  rental_id: string
  amount: number
  mode_of_payment?: string
  reference_no?: string
  reference_date?: string
}

export interface RecordAdvanceResult {
  payment_entry: string
  amount: number
  /** false: saved as a draft for accounting (no accounting role). */
  submitted: boolean
}
