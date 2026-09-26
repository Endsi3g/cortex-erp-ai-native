import type { CompanySettings, ImportBatch, ImportFieldSpec, ImportType, PricingRule, Team } from '@/api/contracts/administration'

/** Mirror of services/pricing.py's standard curve (used when no rule overrides a duration). */
export function standardBillableDays(days: number): number {
  if (days === 1) return 1
  if (days === 2) return 1.5
  if (days === 3) return 2
  if (days === 4) return 2.5
  if (days <= 7) return 3
  if (days <= 14) return 6
  if (days <= 30) return 10
  return Math.round(days * 0.4 * 100) / 100
}

/** Mirror of services/importer.py SPECS (labels and required flags). */
export const DEMO_IMPORT_SPECS: Record<ImportType, ImportFieldSpec[]> = {
  Customers: [
    { field: 'customer_name', label: 'Nom du client', required: true },
    { field: 'customer_type', label: 'Type (Company / Individual)', required: false },
    { field: 'email', label: 'Courriel', required: false },
    { field: 'phone', label: 'Téléphone', required: false },
    { field: 'insurance_valid_until', label: 'Assurance valide jusqu’au', required: false }
  ],
  Equipment: [
    { field: 'item_code', label: 'Code article', required: true },
    { field: 'item_name', label: 'Nom', required: true },
    { field: 'daily_rate', label: 'Tarif journalier', required: true },
    { field: 'replacement_value', label: 'Valeur de remplacement', required: false },
    { field: 'deposit_required', label: 'Dépôt requis', required: false },
    { field: 'category', label: 'Catégorie', required: false },
    { field: 'is_serialized', label: 'Suivi par numéro de série', required: false }
  ],
  'Serial Numbers': [
    { field: 'serial_no', label: 'Numéro de série', required: true },
    { field: 'item_code', label: 'Code article', required: true },
    { field: 'consignment_owner', label: 'Propriétaire (code)', required: false },
    { field: 'warranty_expiry_date', label: 'Fin de garantie', required: false }
  ]
}

export const initialPricingRules: PricingRule[] = [
  { name: 'DEMO-7J', calendar_days: 7, billable_days: 3, is_active: true, description: 'Semaine = 3 jours', modified: '2026-08-12 10:00:00', modified_by: 'demo@cortex.local' },
  { name: 'DEMO-30J', calendar_days: 30, billable_days: 10, is_active: true, description: 'Mois = 10 jours', modified: '2026-08-12 10:00:00', modified_by: 'demo@cortex.local' }
]

export const initialCompanySettings: CompanySettings = {
  advance_percentage: 30,
  include_equipment_guarantee: true,
  taxes_and_charges: 'TPS/TVQ QC - DEMO',
  damage_item: null,
  loss_item: null,
  configured: false
}

export const initialTeam: Team = {
  users: [
    { user: 'demo@cortex.local', full_name: 'Démo Admin', enabled: true, last_login: '2026-09-02 08:00:00', roles: ['Cortex System Manager', 'System Manager'], is_self: true },
    { user: 'alex.ops@cortex.demo', full_name: 'Alex Tremblay', enabled: true, last_login: '2026-09-02 07:45:00', roles: ['Cortex Operations Manager', 'Rental Manager'], is_self: false },
    { user: 'sam.entrepot@cortex.demo', full_name: 'Sam Gagnon', enabled: true, last_login: '2026-09-01 16:10:00', roles: ['Cortex Counter Staff', 'Rental Operator'], is_self: false },
    { user: 'lea.finance@cortex.demo', full_name: 'Léa Roy', enabled: true, last_login: null, roles: ['Accounts User', 'Cortex Finance Manager'], is_self: false }
  ],
  service_accounts: [
    { user: 'agent-intake@cortex.demo', full_name: 'Agent intake', enabled: true, last_login: '2026-09-02 08:34:00', roles: ['Agent Service Account', 'Cortex Agent Intake'], is_self: false }
  ],
  manageable_roles: [
    'Cortex Operations Manager', 'Cortex Counter Staff', 'Cortex Inventory Manager', 'Cortex Finance Manager',
    'Cortex Consignment Manager', 'Cortex Account Reviewer', 'Rental Manager', 'Rental Operator',
    'Pricing Manager', 'Auditor', 'Cortex Read Only'
  ]
}

export const initialImportBatches: ImportBatch[] = [
  {
    name: 'DEMO-IMP-00001', import_type: 'Customers', status: 'Imported', source_file_name: 'clients-2025.csv',
    total_rows: 3, valid_rows: 3, error_rows: 0, imported_rows: 3, created_by: 'demo@cortex.local', created_at: '2026-08-20 09:00:00',
    imported_at: '2026-08-20 09:05:00', imported_by: 'demo@cortex.local', mapping: null, row_errors: [],
    records: [2, 3, 4].map(line => ({ line, doctype: 'Customer', name: `DEMO-CUST-IMP-${line}`, rolled_back: false })),
    rolled_back_by: null, rolled_back_at: null
  }
]
