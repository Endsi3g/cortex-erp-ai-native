import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { i18n } from '@/app/i18n'
import { createAppRouter } from '@/app/router'
import { setCortexApiClient } from '@/api'
import { MockCortexApiClient } from '@/api/mock'
import { HttpCortexApiClient } from '@/api/adapters/HttpCortexApiClient'
import { demoProfitAndLoss } from '@/api/mock/fixtures/finance'
import { LatencySimulator } from '@/api/mock/LatencySimulator'
import { useSessionStore } from '@/stores/session'
import { csvCell, toCsv } from '@/utils/csv'
import PnlTable from '@/features/finance/components/PnlTable.vue'
import ProfitAndLossView from '@/features/finance/views/ProfitAndLossView.vue'

const report = demoProfitAndLoss()

function mountTable() {
  return mount(PnlTable, {
    props: { accounts: report.accounts, periods: report.periods, currency: 'CAD' },
    global: { plugins: [i18n] }
  })
}

describe('PnlTable', () => {
  it('renders the account tree depth-first with row numbers', () => {
    const rows = mountTable().findAll('tbody tr')
    expect(rows.map(r => r.findAll('td')[1].text())).toEqual([
      'Revenus', 'Revenus directs', 'Locations d’équipement', 'Charges', 'Charges directes', 'Coût des ventes', 'Charges indirectes', 'Salaires'
    ])
    expect(rows[0].findAll('td')[0].text()).toBe('1')
    expect(rows[0].classes()).toContain('font-semibold')
    expect(rows[1].classes()).not.toContain('font-semibold')
  })

  it('collapses a group', async () => {
    const wrapper = mountTable()
    await wrapper.find('button[aria-expanded="true"]').trigger('click')
    const names = wrapper.findAll('tbody tr').map(r => r.findAll('td')[1].text())
    expect(names).not.toContain('Revenus directs')
    expect(names).toContain('Charges')
  })

  it('filters by account name and keeps the ancestors for context', async () => {
    const wrapper = mountTable()
    await wrapper.find('input[type="search"]').setValue('salaires')
    const names = wrapper.findAll('tbody tr').map(r => r.findAll('td')[1].text())
    expect(names).toEqual(['Charges', 'Charges indirectes', 'Salaires'])
  })

  it('supports numeric comparisons in period filters', async () => {
    const wrapper = mountTable()
    const inputs = wrapper.findAll('input[type="search"]')
    await inputs[3].setValue('>500000')
    const names = wrapper.findAll('tbody tr').map(r => r.findAll('td')[1].text())
    expect(names).toContain('Revenus')
    expect(names).not.toContain('Salaires')
  })
})

describe('ProfitAndLossView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    LatencySimulator.setEnabled(false)
    const session = useSessionStore()
    session.currentUser = { id: 'fin@x.test', email: 'fin@x.test', full_name: 'Finance', roles: ['Cortex Finance Manager'], permissions: ['cortex:finance:view'] }
    session.isAuthenticated = true
    session.userCompanies = [{ id: 'DEMO Cortex Cinema Rentals', name: 'DEMO Cortex Cinema Rentals', code: 'CCR' }]
    session.activeCompanyId = 'DEMO Cortex Cinema Rentals'
  })

  async function mountView() {
    const router = createAppRouter(true)
    await router.push('/finance/profit-and-loss')
    const wrapper = mount(ProfitAndLossView, { global: { plugins: [i18n, router] } })
    await flushPromises()
    await new Promise(resolve => setTimeout(resolve, 300))
    await flushPromises()
    return wrapper
  }

  it('labels demo data and shows the ERPNext-style summary', async () => {
    setCortexApiClient(new MockCortexApiClient())
    const wrapper = await mountView()
    expect(wrapper.find('[role="status"]').text()).toBe('DEMO')
    expect(wrapper.text()).toContain('Total des revenus')
    expect(wrapper.text()).toMatch(/1\s000\s000,00/)
  })

  it('shows the server reason instead of zeros when ERPNext cannot run the report', async () => {
    const client = new MockCortexApiClient()
    vi.spyOn(client, 'getProfitAndLoss').mockResolvedValue({
      ...report, provenance: 'api', available: false, reason: 'Exercice fermé.', totalIncome: null, totalExpense: null, netProfit: null, periods: [], accounts: []
    })
    setCortexApiClient(client)
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('Rapport indisponible')
    expect(wrapper.text()).toContain('Exercice fermé.')
    expect(wrapper.text()).not.toContain('Total des revenus')
  })
})

describe('HttpCortexApiClient.getProfitAndLoss', () => {
  it('sends only the filters of the chosen period mode, with dimensions flattened', async () => {
    const get = vi.fn().mockResolvedValue({ message: { data: report } })
    const client = new HttpCortexApiClient({ get, post: vi.fn() } as never)
    await client.getProfitAndLoss({
      filter_based_on: 'Fiscal Year', from_fiscal_year: '2024-2025', to_fiscal_year: '2024-2025', from_date: '2024-01-01', to_date: '2024-12-31',
      periodicity: 'Quarterly', accumulated_values: true, include_default_book_entries: false, dimensions: { branch: 'Montréal' }
    })
    const [path, params] = get.mock.calls[0]
    expect(path).toBe('/cortex_rental.api.v1.accounting.get_profit_and_loss')
    expect(params).toMatchObject({ from_fiscal_year: '2024-2025', periodicity: 'Quarterly', accumulated_values: '1', include_default_book_entries: '0', branch: 'Montréal' })
    expect(params).not.toHaveProperty('from_date')
    expect(params).not.toHaveProperty('filter_based_on')
  })
})

describe('CSV export', () => {
  it('neutralises spreadsheet formulas and quotes separators', () => {
    expect(csvCell('=HYPERLINK("x")')).toBe(`"'=HYPERLINK(""x"")"`)
    expect(csvCell('@SUM(A1)')).toBe("'@SUM(A1)")
    expect(csvCell(-120.5)).toBe('-120.5')
    expect(toCsv([['Compte', 'T1'], ['Ventes, locations', 10]])).toBe('Compte,T1\r\n"Ventes, locations",10')
  })
})
