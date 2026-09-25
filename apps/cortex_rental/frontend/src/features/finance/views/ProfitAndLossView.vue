<template>
  <div class="flex min-h-full flex-col bg-surface-white print:block">
    <PageHeader :title="t('routes.finance_pnl')">
      <template #title-suffix>
        <Tooltip v-if="report?.provenance === 'mock'" :text="t('finance.pnl.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Dropdown :options="statementOptions" align="end">
          <Button size="sm" variant="subtle" class="print:hidden">
            {{ t('finance.pnl.financial_statements') }}
            <template #suffix><ChevronsUpDown class="size-4 text-ink-gray-5" :stroke-width="1.5" /></template>
          </Button>
        </Dropdown>
        <Dropdown :options="actionOptions" align="end">
          <Button size="sm" variant="subtle" class="print:hidden">
            {{ t('finance.pnl.actions') }}
            <template #suffix><ChevronsUpDown class="size-4 text-ink-gray-5" :stroke-width="1.5" /></template>
          </Button>
        </Dropdown>
        <Tooltip :text="t('finance.pnl.refresh')">
          <Button size="sm" variant="subtle" class="w-8 print:hidden" :aria-label="t('finance.pnl.refresh')" :loading="loading" @click="loadReport">
            <template #icon><RefreshCw class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Tooltip>
        <Dropdown :options="moreOptions" align="end">
          <Button size="sm" variant="subtle" class="w-8 print:hidden" :aria-label="t('finance.pnl.more')">
            <template #icon><Ellipsis class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Dropdown>
      </template>
    </PageHeader>

    <PageFilters :label="t('finance.pnl.filters')" class="print:hidden">
      <Select
        :model-value="session.activeCompanyId || undefined"
        :options="companyOptions"
        :placeholder="t('finance.pnl.company')"
        :aria-label="t('finance.pnl.company')"
        @update:model-value="onCompanyChange"
      >
        <template #suffix><span /></template>
      </Select>
      <Select
        :model-value="filters.finance_book"
        :options="optionalOptions(options?.finance_books, t('finance.pnl.finance_book'))"
        :placeholder="t('finance.pnl.finance_book')"
        :aria-label="t('finance.pnl.finance_book')"
        @update:model-value="(value: unknown) => (filters.finance_book = fromOptional(value))"
      >
        <template #suffix><span /></template>
      </Select>
      <Select
        v-model="filters.filter_based_on"
        :options="basedOnOptions"
        :aria-label="t('finance.pnl.filter_based_on')"
      >
        <template #suffix><ChevronsUpDown class="ml-auto size-4 shrink-0 text-ink-gray-5" :stroke-width="1.5" /></template>
      </Select>
      <template v-if="filters.filter_based_on === 'Fiscal Year'">
        <Select
          v-model="filters.from_fiscal_year"
          :options="fiscalYearOptions"
          :placeholder="t('finance.pnl.from_fiscal_year')"
          :aria-label="t('finance.pnl.from_fiscal_year')"
        >
          <template #suffix><span /></template>
        </Select>
        <Select
          v-model="filters.to_fiscal_year"
          :options="fiscalYearOptions"
          :placeholder="t('finance.pnl.to_fiscal_year')"
          :aria-label="t('finance.pnl.to_fiscal_year')"
        >
          <template #suffix><span /></template>
        </Select>
      </template>
      <template v-else>
        <TextInput v-model="filters.from_date" type="date" size="sm" variant="subtle" :aria-label="t('finance.pnl.from_date')" />
        <TextInput v-model="filters.to_date" type="date" size="sm" variant="subtle" :aria-label="t('finance.pnl.to_date')" />
      </template>
      <Select
        v-model="filters.periodicity"
        :options="periodicityOptions"
        :aria-label="t('finance.pnl.periodicity')"
      >
        <template #suffix><ChevronsUpDown class="ml-auto size-4 shrink-0 text-ink-gray-5" :stroke-width="1.5" /></template>
      </Select>

      <Select
        :model-value="filters.presentation_currency"
        :options="optionalOptions(options?.currencies, t('finance.pnl.currency'))"
        :placeholder="t('finance.pnl.currency')"
        :aria-label="t('finance.pnl.currency')"
        @update:model-value="(value: unknown) => (filters.presentation_currency = fromOptional(value))"
      >
        <template #suffix><ChevronsUpDown class="ml-auto size-4 shrink-0 text-ink-gray-5" :stroke-width="1.5" /></template>
      </Select>
      <Select
        :model-value="filters.cost_center"
        :options="optionalOptions(options?.cost_centers, t('finance.pnl.cost_center'))"
        :placeholder="t('finance.pnl.cost_center')"
        :aria-label="t('finance.pnl.cost_center')"
        @update:model-value="(value: unknown) => (filters.cost_center = fromOptional(value))"
      >
        <template #suffix><span /></template>
      </Select>
      <Select
        v-for="dimension in options?.dimensions ?? []"
        :key="dimension.fieldname"
        :model-value="filters.dimensions?.[dimension.fieldname]"
        :options="optionalOptions(dimension.options, dimension.label)"
        :placeholder="dimension.label"
        :aria-label="dimension.label"
        @update:model-value="(value: unknown) => setDimension(dimension.fieldname, fromOptional(value))"
      >
        <template #suffix><span /></template>
      </Select>
      <Select
        :model-value="filters.project"
        :options="optionalOptions(options?.projects, t('finance.pnl.project'))"
        :placeholder="t('finance.pnl.project')"
        :aria-label="t('finance.pnl.project')"
        @update:model-value="(value: unknown) => (filters.project = fromOptional(value))"
      >
        <template #suffix><span /></template>
      </Select>
      <Select
        v-model="filters.selected_view"
        :options="reportViewOptions"
        :aria-label="t('finance.pnl.report_view')"
      >
        <template #suffix><ChevronsUpDown class="ml-auto size-4 shrink-0 text-ink-gray-5" :stroke-width="1.5" /></template>
      </Select>
      <div class="flex h-7 items-center">
        <Checkbox v-model="filters.accumulated_values" :label="t('finance.pnl.accumulated_values')" />
      </div>

      <div class="flex h-7 items-center sm:col-span-2">
        <Checkbox v-model="filters.include_default_book_entries" :label="t('finance.pnl.include_default_book_entries')" />
      </div>
    </PageFilters>

    <div v-if="errorMessage" class="mx-6 mt-10 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-3" role="alert">
      <p class="text-base font-medium text-ink-red-4">
        {{ permissionDenied ? t('finance.pnl.permission_denied') : t('finance.pnl.load_failed') }}
      </p>
      <p class="mt-1 text-p-sm text-ink-gray-7">{{ errorMessage }}</p>
      <Button v-if="!permissionDenied" class="mt-3" size="sm" variant="subtle" @click="loadReport">{{ t('finance.pnl.retry') }}</Button>
    </div>

    <div v-else-if="loading && !report" class="mx-6 mt-10 flex items-center gap-2 text-base text-ink-gray-5" role="status">
      <LoadingIndicator class="size-4" /> {{ t('finance.pnl.loading') }}
    </div>

    <div v-else-if="report && !report.available" class="mx-6 mt-10 rounded border border-outline-amber-1 bg-surface-amber-1 px-4 py-3" role="alert">
      <p class="text-base font-medium text-ink-amber-3">{{ t('finance.pnl.unavailable') }}</p>
      <p class="mt-1 text-p-sm text-ink-gray-7">{{ report.reason }}</p>
    </div>

    <template v-else-if="report">
      <PnlKpiSummary
        :total-income="report.totalIncome"
        :total-expense="report.totalExpense"
        :net-profit="report.netProfit"
        :currency="report.currency"
      />
      <PnlChart v-if="showChart && report.periods.length" :periods="report.periods" :currency="report.currency" />
      <div v-else class="h-6" />
      <PnlTable
        :accounts="report.accounts"
        :periods="report.periods"
        :currency="report.currency"
        @open-ledger="openLedger"
      />
      <p v-if="report.accounts.length === 0" class="px-6 py-4 text-p-sm text-ink-gray-5">
        {{ t('finance.pnl.no_gl_entries') }}
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Checkbox, Dropdown, LoadingIndicator, Select, TextInput, Tooltip } from 'frappe-ui'
import { ChevronsUpDown, Ellipsis, RefreshCw } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import { getCortexApiClient } from '@/api'
import { CortexApiError } from '@/api/adapters/httpClient'
import type { PnlAccountRow, PnlFilterOptions, PnlFilters, PnlPeriodicity, PnlReport, PnlReportView } from '@/api/contracts'
import { useSessionStore } from '@/stores/session'
import { toCsv, downloadCsv } from '@/utils/csv'
import PnlKpiSummary from '../components/PnlKpiSummary.vue'
import PnlChart from '../components/PnlChart.vue'
import PnlTable from '../components/PnlTable.vue'

const NONE = '__none__'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const options = ref<PnlFilterOptions | null>(null)
const report = ref<PnlReport | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const permissionDenied = ref(false)
const showChart = ref(true)

const filters = reactive<PnlFilters>({
  filter_based_on: 'Fiscal Year',
  periodicity: 'Quarterly',
  selected_view: 'Report',
  accumulated_values: true,
  include_default_book_entries: true,
  dimensions: {}
})

const companyOptions = computed(() => session.userCompanies.map(company => ({ label: company.name, value: company.id })))
const fiscalYearOptions = computed(() => (options.value?.fiscal_years ?? []).map(fy => ({ label: fy.name, value: fy.name })))
const basedOnOptions = computed(() => [
  { label: t('finance.pnl.based_on_fiscal_year'), value: 'Fiscal Year' },
  { label: t('finance.pnl.based_on_date_range'), value: 'Date Range' }
])
const periodicityOptions = computed(() =>
  (options.value?.periodicities ?? ['Monthly', 'Quarterly', 'Half-Yearly', 'Yearly']).map(value => ({ label: t(`finance.pnl.periodicity_${value}`), value }))
)
const reportViewOptions = computed(() =>
  (options.value?.report_views ?? ['Report', 'Growth', 'Margin']).map(value => ({ label: t(`finance.pnl.view_${value}`), value }))
)

function optionalOptions(values: string[] | undefined, emptyLabel: string) {
  return [{ label: `${emptyLabel} — ${t('finance.pnl.any')}`, value: NONE }, ...(values ?? []).map(value => ({ label: value, value }))]
}

function fromOptional(value: unknown): string | undefined {
  return typeof value === 'string' && value !== NONE ? value : undefined
}

function setDimension(fieldname: string, value: string | undefined) {
  const next = { ...(filters.dimensions ?? {}) }
  if (value) next[fieldname] = value
  else delete next[fieldname]
  filters.dimensions = next
}

async function onCompanyChange(companyId: unknown) {
  if (typeof companyId === 'string' && (await session.switchCompany(companyId))) {
    await loadOptions()
  }
}

// ---- URL <-> filters (shareable links) ---------------------------------
const QUERY_KEYS = ['finance_book', 'filter_based_on', 'from_fiscal_year', 'to_fiscal_year', 'from_date', 'to_date', 'periodicity', 'presentation_currency', 'cost_center', 'project', 'selected_view'] as const

function readQuery() {
  const q = route.query
  for (const key of QUERY_KEYS) {
    if (typeof q[key] === 'string' && q[key]) (filters as Record<string, unknown>)[key] = q[key]
  }
  if (q.accumulated_values === '0') filters.accumulated_values = false
  if (q.include_default_book_entries === '0') filters.include_default_book_entries = false
}

function writeQuery() {
  const query: Record<string, string> = {}
  for (const key of QUERY_KEYS) {
    const value = filters[key]
    if (typeof value === 'string' && value) query[key] = value
  }
  query.accumulated_values = filters.accumulated_values ? '1' : '0'
  query.include_default_book_entries = filters.include_default_book_entries ? '1' : '0'
  void router.replace({ query })
}

// ---- data ----------------------------------------------------------------
function describeError(error: unknown) {
  permissionDenied.value = error instanceof CortexApiError && error.isPermissionError
  errorMessage.value = error instanceof Error ? error.message : String(error)
}

async function loadOptions() {
  errorMessage.value = ''
  try {
    options.value = await getCortexApiClient().getPnlFilterOptions()
    const current = options.value.current_fiscal_year ?? undefined
    if (!filters.from_fiscal_year || !fiscalYearOptions.value.some(o => o.value === filters.from_fiscal_year)) filters.from_fiscal_year = current
    if (!filters.to_fiscal_year || !fiscalYearOptions.value.some(o => o.value === filters.to_fiscal_year)) filters.to_fiscal_year = current
    await loadReport()
  } catch (error) {
    describeError(error)
  }
}

const periodReady = computed(() =>
  filters.filter_based_on === 'Fiscal Year'
    ? Boolean(filters.from_fiscal_year && filters.to_fiscal_year)
    : Boolean(filters.from_date && filters.to_date)
)

async function loadReport() {
  if (!periodReady.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    report.value = await getCortexApiClient().getProfitAndLoss({ ...filters })
  } catch (error) {
    describeError(error)
  } finally {
    loading.value = false
  }
}

let debounce: ReturnType<typeof setTimeout> | undefined
watch(
  () => JSON.stringify(filters),
  () => {
    writeQuery()
    clearTimeout(debounce)
    debounce = setTimeout(loadReport, 250)
  }
)

onMounted(() => {
  readQuery()
  void loadOptions()
})

// ---- actions --------------------------------------------------------------
function deskReportUrl(reportName: string, extra: Record<string, string | undefined> = {}) {
  const params = new URLSearchParams()
  if (session.activeCompanyId) params.set('company', session.activeCompanyId)
  for (const [key, value] of Object.entries(extra)) if (value) params.set(key, value)
  return `/app/query-report/${encodeURIComponent(reportName)}?${params.toString()}`
}

function openLedger(row: PnlAccountRow) {
  window.open(
    deskReportUrl('General Ledger', { account: row.id, from_date: report.value?.periodStart ?? undefined, to_date: report.value?.periodEnd ?? undefined }),
    '_blank',
    'noopener'
  )
}

function exportCsv() {
  if (!report.value) return
  const periods = report.value.periods
  const rows: Array<Array<string | number>> = [[t('finance.pnl.account'), ...periods.map(p => p.label)]]
  const walk = (accounts: PnlAccountRow[]) => {
    for (const account of accounts) {
      rows.push([`${'  '.repeat(account.depth)}${account.name}`, ...periods.map(p => account.values[p.key] ?? 0)])
      walk(account.children)
    }
  }
  walk(report.value.accounts)
  rows.push([t('finance.pnl.total_income'), ...periods.map(p => p.income)])
  rows.push([t('finance.pnl.total_expense'), ...periods.map(p => p.expense)])
  rows.push([t('finance.pnl.net_profit_loss'), ...periods.map(p => p.profitLoss)])
  downloadCsv(`compte-de-resultat-${report.value.company}-${report.value.periodStart ?? ''}.csv`, toCsv(rows))
}

const statementOptions = computed(() => [
  { label: t('routes.finance_pnl'), selected: true, onClick: () => undefined },
  { label: t('finance.pnl.balance_sheet'), onClick: () => window.open(deskReportUrl('Balance Sheet'), '_blank', 'noopener') },
  { label: t('finance.pnl.cash_flow'), onClick: () => window.open(deskReportUrl('Cash Flow'), '_blank', 'noopener') }
])

const actionOptions = computed(() => [
  { label: t('finance.pnl.export_csv'), onClick: exportCsv, disabled: !report.value?.available },
  { label: t('finance.pnl.print'), onClick: () => window.print(), disabled: !report.value?.available },
  { label: t('finance.pnl.open_in_erpnext'), onClick: () => window.open(deskReportUrl('Profit and Loss Statement'), '_blank', 'noopener') }
])

const moreOptions = computed(() => [
  { label: showChart.value ? t('finance.pnl.hide_chart') : t('finance.pnl.show_chart'), onClick: () => (showChart.value = !showChart.value) },
  {
    label: t('finance.pnl.reset_filters'),
    onClick: () => {
      Object.assign(filters, {
        finance_book: undefined,
        filter_based_on: 'Fiscal Year',
        from_fiscal_year: options.value?.current_fiscal_year ?? undefined,
        to_fiscal_year: options.value?.current_fiscal_year ?? undefined,
        from_date: undefined,
        to_date: undefined,
        periodicity: 'Quarterly' as PnlPeriodicity,
        presentation_currency: undefined,
        cost_center: undefined,
        project: undefined,
        selected_view: 'Report' as PnlReportView,
        accumulated_values: true,
        include_default_book_entries: true,
        dimensions: {}
      })
    }
  }
])
</script>
