import type { ConsignmentOwner, OwnerStatementSafe, ConsignmentDashboardData } from '@/types/consignment'

export const initialOwners: ConsignmentOwner[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-OWN-001',
    owner_code: 'MINERVA',
    display_name: 'Minerva Equipment Assets Ltd.',
    company_name: 'Minerva Assets Corp.',
    contact_email: 'payouts@minerva-assets.demo',
    contact_phone: '+1 514 555 0199',
    default_commission_percentage: 70, // 70% to owner
    active_serials_count: 2,
    pending_payout_amount: 3150,
    currency: 'CAD'
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-OWN-002',
    owner_code: 'VORTEX',
    display_name: 'Vortex Optics Corp.',
    company_name: 'Vortex Optics Inc.',
    contact_email: 'finance@vortex-optics.demo',
    contact_phone: '+1 438 555 0133',
    default_commission_percentage: 65, // 65% to owner
    active_serials_count: 1,
    pending_payout_amount: 1852.50,
    currency: 'CAD'
  }
]

export const initialConsignmentDashboard: ConsignmentDashboardData = {
  provenance: 'demo',
  last_synced_at: '2026-09-02T16:00:00Z',
  current_month_total_payout: 5002.50,
  previous_month_total_payout: 8420.00,
  active_owners_count: 2,
  active_consigned_serials_count: 3,
  top_earning_items: [
    {
      item_code: 'DEMO-ITM-ALX35',
      item_name: 'ARRI Alexa 35 Camera Package',
      owner_code: 'MINERVA',
      revenue_generated: 4500,
      owner_payout: 3150
    },
    {
      item_code: 'DEMO-ITM-CKE-S4',
      item_name: 'Cooke S4/i Prime Lens Set',
      owner_code: 'VORTEX',
      revenue_generated: 2850,
      owner_payout: 1852.50
    }
  ],
  pending_statements: [
    {
      owner_id: 'DEMO-OWN-001',
      owner_name: 'Minerva Equipment Assets Ltd.',
      period: '2026-08',
      amount_due: 3150,
      status: 'draft'
    },
    {
      owner_id: 'DEMO-OWN-002',
      owner_name: 'Vortex Optics Corp.',
      period: '2026-08',
      amount_due: 1852.50,
      status: 'draft'
    }
  ]
}

export const initialOwnerStatements: Record<string, OwnerStatementSafe> = {
  'DEMO-OWN-001_2026-08': {
    owner: {
      id: 'DEMO-OWN-001',
      display_name: 'Minerva Equipment Assets Ltd.',
      code: 'MINERVA'
    },
    period: {
      start: '2026-08-01',
      end: '2026-08-31',
      timezone: 'America/Toronto'
    },
    currency: 'CAD',
    totals: {
      eligible_net_revenue: 4500,
      owner_amount_due: 3150
    },
    lines: [
      {
        serial_number: 'DEMO-SN-ALX-001',
        equipment_name: 'ARRI Alexa 35 Camera Package',
        rental_start_date: '2026-08-10',
        rental_end_date: '2026-08-17',
        billable_days: 3,
        rate: 1500,
        discount_amount: 0,
        consignment_percentage: 70,
        owner_amount: 3150,
        invoice_reference: 'INV-2026-08-012'
      }
    ],
    generated_at: '2026-09-01T00:00:00Z',
    snapshot_version: 'v1.0'
  },
  'DEMO-OWN-002_2026-08': {
    owner: {
      id: 'DEMO-OWN-002',
      display_name: 'Vortex Optics Corp.',
      code: 'VORTEX'
    },
    period: {
      start: '2026-08-01',
      end: '2026-08-31',
      timezone: 'America/Toronto'
    },
    currency: 'CAD',
    totals: {
      eligible_net_revenue: 2850,
      owner_amount_due: 1852.50
    },
    lines: [
      {
        serial_number: 'DEMO-SN-CKE-101',
        equipment_name: 'Cooke S4/i Prime Lens Set',
        rental_start_date: '2026-08-12',
        rental_end_date: '2026-08-19',
        billable_days: 3,
        rate: 950,
        discount_amount: 0,
        consignment_percentage: 65,
        owner_amount: 1852.50,
        invoice_reference: 'INV-2026-08-014'
      }
    ],
    generated_at: '2026-09-01T00:00:00Z',
    snapshot_version: 'v1.0'
  }
}
