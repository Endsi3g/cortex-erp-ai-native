import type { PnlAccountRow, PnlFilterOptions, PnlReport } from '../../contracts'

/**
 * DEMO data for the explicit mock client only (tests, screenshots). Shaped
 * like the ERPNext reference capture: quarterly, income only in the last
 * two quarters. Never used when the app talks to Frappe.
 */
export const demoPnlFilterOptions: PnlFilterOptions = {
  company: 'DEMO Cortex Cinema Rentals',
  company_currency: 'CAD',
  fiscal_years: [
    { name: '2024-2025', start: '2024-04-01', end: '2025-03-31' },
    { name: '2023-2024', start: '2023-04-01', end: '2024-03-31' }
  ],
  current_fiscal_year: '2024-2025',
  finance_books: [],
  cost_centers: ['DEMO Main - CCR'],
  projects: [],
  currencies: ['CAD', 'USD'],
  dimensions: [{ fieldname: 'branch', label: 'Branch', options: ['DEMO Montréal'] }],
  periodicities: ['Monthly', 'Quarterly', 'Half-Yearly', 'Yearly'],
  report_views: ['Report', 'Growth', 'Margin']
}

const Q = ['jun_2024', 'sep_2024', 'dec_2024', 'mar_2025'] as const

function row(id: string, name: string, depth: number, values: number[], children: PnlAccountRow[] = []): PnlAccountRow {
  return {
    id,
    name,
    depth,
    type: children.length ? 'group' : 'account',
    values: Object.fromEntries(Q.map((key, index) => [key, values[index]])),
    total: values[values.length - 1],
    children
  }
}

export function demoProfitAndLoss(): PnlReport {
  return {
    provenance: 'mock',
    available: true,
    company: demoPnlFilterOptions.company,
    currency: 'CAD',
    periodStart: '2024-04-01',
    periodEnd: '2025-03-31',
    totalIncome: 1000000,
    totalExpense: 620000,
    netProfit: 380000,
    periods: [
      { key: 'jun_2024', label: 'Avr. 24–juin 24', income: 0, expense: 0, profitLoss: 0 },
      { key: 'sep_2024', label: 'Juil. 24–sept. 24', income: 0, expense: 0, profitLoss: 0 },
      { key: 'dec_2024', label: 'Oct. 24–déc. 24', income: 1000000, expense: 620000, profitLoss: 380000 },
      { key: 'mar_2025', label: 'Janv. 25–mars 25', income: 1000000, expense: 620000, profitLoss: 380000 }
    ],
    accounts: [
      row('Income - CCR', 'Revenus', 0, [0, 0, 1000000, 1000000], [
        row('Direct Income - CCR', 'Revenus directs', 1, [0, 0, 1000000, 1000000], [
          row('Sales - CCR', 'Locations d’équipement', 2, [0, 0, 1000000, 1000000])
        ])
      ]),
      row('Expenses - CCR', 'Charges', 0, [0, 0, 620000, 620000], [
        row('Direct Expenses - CCR', 'Charges directes', 1, [0, 0, 420000, 420000], [
          row('Cost of Goods Sold - CCR', 'Coût des ventes', 2, [0, 0, 420000, 420000])
        ]),
        row('Indirect Expenses - CCR', 'Charges indirectes', 1, [0, 0, 200000, 200000], [
          row('Salary - CCR', 'Salaires', 2, [0, 0, 200000, 200000])
        ])
      ])
    ]
  }
}
