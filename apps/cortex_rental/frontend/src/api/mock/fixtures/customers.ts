export interface DemoCustomer {
  id: string
  name: string
  contact_email: string
  phone: string
  is_verified: boolean
  insurance_valid_until: string
  insurance_coverage_cad: number
  deposit_on_file_cad: number
  account_status: 'Good' | 'Hold' | 'Review_Needed'
}

export const initialCustomers: DemoCustomer[] = [
  {
    id: 'DEMO-CUST-001',
    name: 'Production Nord Inc.',
    contact_email: 'production@nord-film.demo',
    phone: '+1 514 555 0192',
    is_verified: true,
    insurance_valid_until: '2026-12-31',
    insurance_coverage_cad: 5000000,
    deposit_on_file_cad: 10000,
    account_status: 'Good'
  },
  {
    id: 'DEMO-CUST-002',
    name: 'Studio Lumière Montréal',
    contact_email: 'ops@studiolumiere.demo',
    phone: '+1 514 555 0148',
    is_verified: true,
    insurance_valid_until: '2026-10-15',
    insurance_coverage_cad: 2000000,
    deposit_on_file_cad: 5000,
    account_status: 'Good'
  },
  {
    id: 'DEMO-CUST-003',
    name: 'Trequista Events',
    contact_email: 'broadcast@trequista.demo',
    phone: '+1 438 555 0177',
    is_verified: false,
    insurance_valid_until: '2026-08-30', // expired
    insurance_coverage_cad: 1000000,
    deposit_on_file_cad: 0,
    account_status: 'Review_Needed'
  }
]
