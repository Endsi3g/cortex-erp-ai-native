/**
 * Finance contracts — Profit and Loss Statement, backed by ERPNext's own
 * `Profit and Loss Statement` report (cortex_rental.api.v1.accounting).
 */

export type PnlPeriodicity = 'Monthly' | 'Quarterly' | 'Half-Yearly' | 'Yearly'
export type PnlReportView = 'Report' | 'Growth' | 'Margin'

export interface PnlFiscalYear {
  name: string
  start: string
  end: string
}

export interface PnlDimension {
  fieldname: string
  label: string
  options: string[]
}

export interface PnlFilterOptions {
  company: string
  company_currency: string | null
  fiscal_years: PnlFiscalYear[]
  current_fiscal_year: string | null
  finance_books: string[]
  cost_centers: string[]
  projects: string[]
  currencies: string[]
  dimensions: PnlDimension[]
  periodicities: PnlPeriodicity[]
  report_views: PnlReportView[]
}

export interface PnlFilters {
  finance_book?: string
  filter_based_on: 'Fiscal Year' | 'Date Range'
  from_fiscal_year?: string
  to_fiscal_year?: string
  from_date?: string
  to_date?: string
  periodicity: PnlPeriodicity
  presentation_currency?: string
  cost_center?: string
  project?: string
  selected_view?: PnlReportView
  accumulated_values: boolean
  include_default_book_entries: boolean
  /** Accounting dimension values keyed by dimension fieldname (e.g. branch). */
  dimensions?: Record<string, string>
}

export interface PnlPeriod {
  key: string
  label: string
  income: number
  expense: number
  profitLoss: number
}

export interface PnlAccountRow {
  id: string
  name: string
  depth: number
  type: 'group' | 'account'
  values: Record<string, number | null>
  total: number | null
  children: PnlAccountRow[]
}

export interface PnlReport {
  /** 'mock' only when the explicit demo client is configured; never set by the server. */
  provenance?: 'api' | 'mock'
  available: boolean
  /** Present when `available` is false: why ERPNext could not produce the report. */
  reason?: string
  company: string
  currency: string | null
  periodStart: string | null
  periodEnd: string | null
  totalIncome: number | null
  totalExpense: number | null
  netProfit: number | null
  periods: PnlPeriod[]
  accounts: PnlAccountRow[]
}
