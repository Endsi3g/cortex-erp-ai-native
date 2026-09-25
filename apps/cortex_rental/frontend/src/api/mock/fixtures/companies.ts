import type { TenantCompany } from '@/types/common'

export const initialCompanies: TenantCompany[] = [
  {
    id: 'DEMO-COMP-001',
    name: 'Cortex Cinema Rentals',
    code: 'CCR',
    currency: 'CAD',
    timezone: 'America/Toronto',
    is_active: true
  },
  {
    id: 'DEMO-COMP-002',
    name: 'Cortex Broadcast Montréal',
    code: 'CBM',
    currency: 'CAD',
    timezone: 'America/Toronto',
    is_active: true
  }
]
