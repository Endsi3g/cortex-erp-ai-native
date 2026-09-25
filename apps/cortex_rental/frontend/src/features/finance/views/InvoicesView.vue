<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.finance_invoices')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock'" :text="t('finance.invoices.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <TabButtons v-model="tab" :buttons="tabs" />
        <Tooltip :text="t('finance.pnl.refresh')">
          <Button size="sm" variant="subtle" class="w-8" :aria-label="t('finance.pnl.refresh')" :loading="loading" @click="load">
            <template #icon><RefreshCw class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Tooltip>
      </template>
    </PageHeader>

    <PageFilters :label="t('finance.invoices.filters')">
      <TextInput
        v-model="search"
        type="search"
        size="sm"
        variant="subtle"
        :placeholder="t('finance.invoices.search')"
        :aria-label="t('finance.invoices.search')"
        class="lg:col-span-2"
      />
      <Select
        v-if="tab === 'invoices'"
        :model-value="status"
        :options="statusOptions"
        :placeholder="t('finance.invoices.status')"
        :aria-label="t('finance.invoices.status')"
        @update:model-value="(value: unknown) => (status = value === ANY ? undefined : (value as InvoiceStatus))"
      >
        <template #suffix><ChevronsUpDown class="ml-auto size-4 shrink-0 text-ink-gray-5" :stroke-width="1.5" /></template>
      </Select>
      <TextInput v-model="fromDate" type="date" size="sm" variant="subtle" :aria-label="t('finance.invoices.from_date')" />
      <TextInput v-model="toDate" type="date" size="sm" variant="subtle" :aria-label="t('finance.invoices.to_date')" />
    </PageFilters>

    <div v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-3" role="alert">
      <p class="text-base font-medium text-ink-red-4">{{ t('finance.invoices.load_failed') }}</p>
      <p class="mt-1 text-p-sm text-ink-gray-7">{{ errorMessage }}</p>
    </div>

    <div class="mt-6">
      <DataTable
        v-if="tab === 'invoices'"
        :label="t('finance.invoices.invoices')"
        :columns="invoiceColumns"
        :rows="invoices"
        :loading="loading"
        :empty-text="t('finance.invoices.no_invoices')"
        :total="total"
        :page="page"
        :page-size="pageSize"
        clickable
        @row-click="row => openDesk('sales-invoice', String(row.name))"
        @update:page="value => (page = value)"
        @update:page-size="value => { pageSize = value; page = 1 }"
      >
        <template #cell-status="{ row }">
          <Badge :theme="statusTheme(String(row.status))" variant="subtle">{{ t(`finance.invoices.status_${String(row.status).replace(/ /g, '_')}`) }}</Badge>
        </template>
        <template #cell-cortex_rental_transaction="{ row }">
          <RouterLink :to="{ name: 'rental-detail', params: { name: String(row.cortex_rental_transaction) } }" class="text-ink-gray-8 underline decoration-outline-gray-3 underline-offset-2 hover:decoration-ink-gray-8" @click.stop>
            {{ row.cortex_rental_transaction }}
          </RouterLink>
        </template>
      </DataTable>

      <DataTable
        v-else
        :label="t('finance.invoices.payments')"
        :columns="paymentColumns"
        :rows="payments"
        :loading="loading"
        :empty-text="t('finance.invoices.no_payments')"
        :total="total"
        :page="page"
        :page-size="pageSize"
        clickable
        @row-click="row => openDesk('payment-entry', String(row.name))"
        @update:page="value => (page = value)"
        @update:page-size="value => { pageSize = value; page = 1 }"
      >
        <template #cell-docstatus="{ row }">
          <Badge :theme="row.docstatus === 1 ? 'green' : 'gray'" variant="subtle">
            {{ row.docstatus === 1 ? t('finance.invoices.payment_submitted') : t('finance.invoices.payment_draft') }}
          </Badge>
        </template>
        <template #cell-cortex_rental_transaction="{ row }">
          <RouterLink :to="{ name: 'rental-detail', params: { name: String(row.cortex_rental_transaction) } }" class="text-ink-gray-8 underline decoration-outline-gray-3 underline-offset-2 hover:decoration-ink-gray-8" @click.stop>
            {{ row.cortex_rental_transaction }}
          </RouterLink>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Select, TabButtons, TextInput, Tooltip } from 'frappe-ui'
import { ChevronsUpDown, RefreshCw } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { InvoiceRow, InvoiceStatus, PaymentRow } from '@/api/contracts'
import { formatDate, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const ANY = '__any__'
const STATUSES: InvoiceStatus[] = ['Draft', 'Unpaid', 'Partly Paid', 'Overdue', 'Paid', 'Return', 'Credit Note Issued', 'Cancelled']

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const tab = ref<'invoices' | 'payments'>(route.query.tab === 'payments' ? 'payments' : 'invoices')
const search = ref(typeof route.query.q === 'string' ? route.query.q : '')
const status = ref<InvoiceStatus | undefined>(STATUSES.includes(route.query.status as InvoiceStatus) ? (route.query.status as InvoiceStatus) : undefined)
const fromDate = ref(typeof route.query.from === 'string' ? route.query.from : '')
const toDate = ref(typeof route.query.to === 'string' ? route.query.to : '')
const page = ref(1)
const pageSize = ref(20)

const invoices = ref<InvoiceRow[]>([])
const payments = ref<PaymentRow[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const provenance = ref<'api' | 'mock' | undefined>()

const tabs = computed(() => [
  { label: t('finance.invoices.invoices'), value: 'invoices' },
  { label: t('finance.invoices.payments'), value: 'payments' }
])
const statusOptions = computed(() => [
  { label: `${t('finance.invoices.status')} — ${t('finance.pnl.any')}`, value: ANY },
  ...STATUSES.map(value => ({ label: t(`finance.invoices.status_${value.replace(/ /g, '_')}`), value }))
])

const money = (value: unknown, currency: unknown) => formatMoney(Number(value ?? 0), String(currency || 'CAD'), locale.value as LocaleType)
const date = (value: unknown) => (value ? formatDate(String(value), locale.value as LocaleType) : '')

const invoiceColumns = computed<DataTableColumn<InvoiceRow>[]>(() => [
  { key: 'name', label: t('finance.invoices.number'), width: '170px' },
  { key: 'customer_name', label: t('finance.invoices.customer'), width: '240px' },
  { key: 'cortex_rental_transaction', label: t('finance.invoices.rental'), width: '170px' },
  { key: 'posting_date', label: t('finance.invoices.date'), width: '120px', format: row => date(row.posting_date) },
  { key: 'status', label: t('finance.invoices.status'), width: '140px' },
  { key: 'grand_total', label: t('finance.invoices.total'), width: '150px', align: 'right', format: row => money(row.grand_total, row.currency) },
  { key: 'total_advance', label: t('finance.invoices.advance'), width: '150px', align: 'right', format: row => money(row.total_advance, row.currency) },
  { key: 'outstanding_amount', label: t('finance.invoices.outstanding'), width: '150px', align: 'right', format: row => money(row.outstanding_amount, row.currency) }
])

const paymentColumns = computed<DataTableColumn<PaymentRow>[]>(() => [
  { key: 'name', label: t('finance.invoices.number'), width: '170px' },
  { key: 'party_name', label: t('finance.invoices.customer'), width: '240px' },
  { key: 'cortex_rental_transaction', label: t('finance.invoices.rental'), width: '170px' },
  { key: 'posting_date', label: t('finance.invoices.date'), width: '120px', format: row => date(row.posting_date) },
  { key: 'mode_of_payment', label: t('finance.invoices.mode'), width: '150px' },
  { key: 'reference_no', label: t('finance.invoices.reference'), width: '150px' },
  { key: 'docstatus', label: t('finance.invoices.state'), width: '130px' },
  { key: 'paid_amount', label: t('finance.invoices.amount'), width: '150px', align: 'right', format: row => money(row.paid_amount, row.currency) }
])

function statusTheme(value: string) {
  return ({ Paid: 'green', 'Partly Paid': 'orange', Unpaid: 'orange', Overdue: 'red', Cancelled: 'red', Draft: 'gray' } as Record<string, string>)[value] ?? 'gray'
}

function openDesk(doctype: string, name: string) {
  window.open(`/app/${doctype}/${encodeURIComponent(name)}`, '_blank', 'noopener')
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  const base = { search: search.value || undefined, from_date: fromDate.value || undefined, to_date: toDate.value || undefined, page: page.value, page_size: pageSize.value }
  try {
    const api = getCortexApiClient()
    if (tab.value === 'invoices') {
      const result = await api.listInvoices({ ...base, status: status.value })
      invoices.value = result.items
      total.value = result.total_count
      provenance.value = result.provenance
    } else {
      const result = await api.listPayments(base)
      payments.value = result.items
      total.value = result.total_count
      provenance.value = result.provenance
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch([tab, search, status, fromDate, toDate], () => {
  page.value = 1
  void router.replace({ query: { tab: tab.value, q: search.value || undefined, status: status.value, from: fromDate.value || undefined, to: toDate.value || undefined } })
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})
watch([page, pageSize], () => void load())
onMounted(load)
</script>
