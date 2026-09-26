/**
 * Administration contracts — cortex_rental.api.v1.admin (policies, team,
 * audit log) and cortex_rental.api.v1.imports (CSV import batches).
 */

export interface PricingRule {
  name: string
  calendar_days: number
  billable_days: number
  is_active: boolean
  description: string
  modified: string
  modified_by: string
}

export interface CompanySettings {
  advance_percentage: number
  include_equipment_guarantee: boolean
  taxes_and_charges: string | null
  damage_item: string | null
  loss_item: string | null
  /** false while the company still runs on defaults (no Cortex Company Settings record). */
  configured: boolean
}

export interface Policies {
  provenance?: 'api' | 'mock'
  rules: PricingRule[]
  curve: Array<{ calendar_days: number; billable_days: number; source: 'rule' | 'standard' }>
  settings: CompanySettings
  tax_templates: string[]
  currency: string | null
  can_edit_pricing: boolean
  can_edit_settings: boolean
}

export interface PricingRuleInput {
  calendar_days: number
  billable_days: number
  description?: string
  is_active: boolean
}

export type CompanySettingsInput = Partial<Omit<CompanySettings, 'configured'>>

export interface TeamMember {
  user: string
  full_name: string
  enabled: boolean
  last_login: string | null
  roles: string[]
  is_self: boolean
}

export interface Team {
  provenance?: 'api' | 'mock'
  users: TeamMember[]
  service_accounts: TeamMember[]
  manageable_roles: string[]
}

export interface AuditRow extends Record<string, unknown> {
  name: string
  timestamp: string
  actor_type: 'Human' | 'Agent' | 'System'
  actor_id: string
  action: string
  entity_type: string
  entity_id: string
  request_id: string | null
}

export interface AuditQuery {
  action?: string
  entity_type?: string
  entity_id?: string
  actor?: string
  actor_type?: string
  from_date?: string
  to_date?: string
  page: number
  page_size: number
}

export interface AuditPage {
  provenance?: 'api' | 'mock'
  items: AuditRow[]
  total_count: number
  page: number
  page_size: number
  entity_types: string[]
}

export interface AuditEventDetail extends AuditRow {
  before_state: unknown
  after_state: unknown
  evidence: unknown
  policy_decision: unknown
}

export type ImportType = 'Customers' | 'Equipment' | 'Serial Numbers'
export type ImportStatus = 'Draft' | 'Validated' | 'Imported' | 'Partially Imported' | 'Rolled Back' | 'Failed'

export interface ImportFieldSpec {
  field: string
  label: string
  required: boolean
}

export interface ImportBatchRow extends Record<string, unknown> {
  name: string
  import_type: ImportType
  status: ImportStatus
  source_file_name: string | null
  total_rows: number
  valid_rows: number
  error_rows: number
  imported_rows: number
  created_by: string
  created_at: string
  imported_at: string | null
}

export interface ImportBatches {
  provenance?: 'api' | 'mock'
  items: ImportBatchRow[]
  specs: Record<ImportType, ImportFieldSpec[]>
}

export interface ImportRowError {
  line: number
  errors: string[]
}

export interface ImportBatch extends ImportBatchRow {
  mapping: Record<string, string | null> | null
  row_errors: ImportRowError[]
  records: Array<{ line: number; doctype: string; name: string; rolled_back: boolean }>
  imported_by: string | null
  rolled_back_by: string | null
  rolled_back_at: string | null
}

export interface ImportAnalysis {
  file_name: string
  headers: string[]
  preview: string[][]
  total_rows: number
  mapping: Record<string, string | null>
}

export interface ImportValidation {
  total_rows: number
  valid_rows: number
  error_rows: number
  errors: ImportRowError[]
  sample: Array<{ line: number; values: Record<string, unknown> }>
}

export interface ImportRollback extends ImportBatch {
  deleted: number
  kept: Array<{ doctype: string; name: string; reason: string }>
}
