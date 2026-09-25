<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="record?.customer_name || String(route.params.customer)">
      <template #title-suffix>
        <InsuranceBadge v-if="record" :status="record.insurance.status" :valid-until="record.insurance.valid_until" />
        <Tooltip v-if="record?.provenance === 'mock'" :text="t('customers.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template v-if="record" #actions>
        <Button size="sm" variant="subtle" @click="openDesk">{{ t('finance.pnl.open_in_erpnext') }}</Button>
        <Button v-if="record.can_verify" size="sm" variant="subtle" @click="openInsurance">{{ t('customers.verify_insurance') }}</Button>
        <Button v-if="session.hasPermission('cortex:quote:create')" size="sm" variant="solid" :route="{ name: 'rental-composer', query: { customer: record.name } }">{{ t('rentals.new_rental') }}</Button>
      </template>
    </PageHeader>

    <p v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>
    <div v-else-if="!record" class="mx-6 mt-10 flex items-center gap-2 text-base text-ink-gray-5" role="status"><LoadingIndicator class="size-4" /> {{ t('table.loading') }}</div>

    <template v-else>
      <dl class="grid grid-cols-2 gap-x-8 gap-y-4 border-b border-outline-gray-1 px-6 py-5 md:grid-cols-4">
        <div><dt class="text-sm text-ink-gray-5">{{ t('customers.type') }}</dt><dd class="mt-1 text-base">{{ t(`customers.type_${record.customer_type}`) }} · {{ record.customer_group }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('consignment_screen.email') }}</dt><dd class="mt-1 truncate text-base">{{ record.email || '—' }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('consignment_screen.phone') }}</dt><dd class="mt-1 text-base">{{ record.phone || '—' }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('customers.insurance') }}</dt><dd class="mt-1 text-base">{{ record.insurance.valid_until ? t('customers.valid_until', { date: date(record.insurance.valid_until) }) : t('customers.insurance_unknown') }}</dd></div>
      </dl>

      <section class="grid grid-cols-2 gap-4 px-6 pt-5 xl:grid-cols-4" :aria-label="t('customers.indicators')">
        <div v-for="card in cards" :key="card.label" class="rounded border border-outline-gray-1 px-4 py-3">
          <p class="text-base text-ink-gray-6">{{ card.label }}</p>
          <p class="mt-2 text-2xl font-semibold tabular-nums" :class="card.alert ? 'text-ink-red-4' : 'text-ink-gray-8'">{{ card.value }}</p>
        </div>
      </section>

      <div class="px-6 pt-6"><TabButtons v-model="tab" :buttons="tabs" /></div>

      <div class="mt-4 pb-8">
        <DataTable v-if="tab === 'rentals'" :label="t('customers.rentals')" :columns="rentalColumns" :rows="rentalRows" row-key="name" :filter-row="false" :empty-text="t('customers.no_rentals')" clickable @row-click="row => router.push({ name: 'rental-detail', params: { name: String(row.name) } })">
          <template #cell-rental_state="{ row }"><RentalStateBadge :state="row.rental_state as RentalStateValue" /></template>
        </DataTable>
        <DataTable v-else-if="tab === 'invoices'" :label="t('finance.invoices.invoices')" :columns="invoiceColumns" :rows="invoiceRows" row-key="name" :filter-row="false" :empty-text="t('finance.invoices.no_invoices')" clickable @row-click="row => desk('sales-invoice', String(row.name))" />
        <DataTable v-else :label="t('finance.invoices.payments')" :columns="paymentColumns" :rows="paymentRows" row-key="name" :filter-row="false" :empty-text="t('finance.invoices.no_payments')" clickable @row-click="row => desk('payment-entry', String(row.name))" />
      </div>
    </template>

    <Dialog v-model="insuranceOpen" :options="{ title: t('customers.verify_insurance'), size: 'md' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl v-model="insuranceDate" type="date" size="sm" variant="subtle" :label="t('customers.insurance_date')" />
          <FormControl v-model="insuranceNote" type="textarea" size="sm" variant="subtle" :label="t('customers.insurance_note')" />
          <p class="text-p-sm text-ink-gray-5">{{ t('customers.insurance_hint') }}</p>
          <p v-if="insuranceError" class="text-p-sm text-ink-red-4" role="alert">{{ insuranceError }}</p>
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="subtle" :disabled="savingInsurance" @click="close">{{ t('common.cancel') }}</Button>
          <Button variant="solid" :loading="savingInsurance" @click="saveInsurance">{{ t('composer.save_changes') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dialog, FormControl, LoadingIndicator, TabButtons, Tooltip, toast } from 'frappe-ui'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { CustomerRecord } from '@/api/contracts'
import type { RentalStateValue } from '@/api/contracts/rentals'
import { formatDate, formatDateTime, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'
import RentalStateBadge from '@/features/rentals/components/RentalStateBadge.vue'
import InsuranceBadge from '../components/InsuranceBadge.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const record = ref<CustomerRecord | null>(null)
const errorMessage = ref('')
const tab = ref<'rentals' | 'invoices' | 'payments'>('rentals')
const insuranceOpen = ref(false)
const insuranceDate = ref('')
const insuranceNote = ref('')
const insuranceError = ref('')
const savingInsurance = ref(false)

const loc = () => locale.value as LocaleType
const money = (value: number) => formatMoney(value, record.value?.currency, loc())
const date = (value: string) => formatDate(value, loc())
const desk = (doctype: string, name: string) => window.open(`/app/${doctype}/${encodeURIComponent(name)}`, '_blank', 'noopener')
const openDesk = () => desk('customer', record.value!.name)

const tabs = computed(() => [
  { label: t('customers.rentals'), value: 'rentals' },
  { label: t('finance.invoices.invoices'), value: 'invoices' },
  { label: t('finance.invoices.payments'), value: 'payments' }
])

const cards = computed(() => {
  const s = record.value!.stats
  return [
    { label: t('customers.rentals'), value: String(s.rentals) },
    { label: t('customers.active'), value: String(s.active_rentals) },
    { label: t('customers.lifetime_value'), value: money(s.lifetime_value) },
    { label: t('finance.invoices.outstanding'), value: money(s.outstanding), alert: s.outstanding > 0 }
  ]
})

type RentalRow = CustomerRecord['rentals'][number] & Record<string, unknown>
type InvoiceRow = CustomerRecord['invoices'][number] & Record<string, unknown>
type PaymentRow = CustomerRecord['payments'][number] & Record<string, unknown>
const rentalRows = computed(() => (record.value?.rentals ?? []) as RentalRow[])
const invoiceRows = computed(() => (record.value?.invoices ?? []) as InvoiceRow[])
const paymentRows = computed(() => (record.value?.payments ?? []) as PaymentRow[])

const rentalColumns = computed<DataTableColumn<RentalRow>[]>(() => [
  { key: 'name', label: t('rentals.col_id'), width: '170px' },
  { key: 'project_name', label: t('rentals.col_project'), width: '240px' },
  { key: 'rental_state', label: t('rentals.col_state'), width: '130px' },
  { key: 'starts_at', label: t('rentals.col_start'), width: '180px', format: row => formatDateTime(row.starts_at, loc()) },
  { key: 'ends_at', label: t('rentals.col_end'), width: '180px', format: row => formatDateTime(row.ends_at, loc()) },
  { key: 'grand_total', label: t('rentals.col_total'), width: '140px', align: 'right', format: row => money(row.grand_total) }
])
const invoiceColumns = computed<DataTableColumn<InvoiceRow>[]>(() => [
  { key: 'name', label: t('finance.invoices.number'), width: '170px' },
  { key: 'posting_date', label: t('finance.invoices.date'), width: '130px', format: row => date(row.posting_date) },
  { key: 'status', label: t('finance.invoices.status'), width: '140px', format: row => t(`finance.invoices.status_${row.status.replace(/ /g, '_')}`) },
  { key: 'rental', label: t('finance.invoices.rental'), width: '170px' },
  { key: 'grand_total', label: t('finance.invoices.total'), width: '140px', align: 'right', format: row => money(row.grand_total) },
  { key: 'outstanding_amount', label: t('finance.invoices.outstanding'), width: '140px', align: 'right', format: row => money(row.outstanding_amount) }
])
const paymentColumns = computed<DataTableColumn<PaymentRow>[]>(() => [
  { key: 'name', label: t('finance.invoices.number'), width: '170px' },
  { key: 'posting_date', label: t('finance.invoices.date'), width: '130px', format: row => date(row.posting_date) },
  { key: 'mode_of_payment', label: t('finance.invoices.mode'), width: '160px' },
  { key: 'rental', label: t('finance.invoices.rental'), width: '170px' },
  { key: 'docstatus', label: t('finance.invoices.state'), width: '160px', format: row => (row.docstatus === 1 ? t('finance.invoices.payment_submitted') : t('finance.invoices.payment_draft')) },
  { key: 'paid_amount', label: t('finance.invoices.amount'), width: '140px', align: 'right', format: row => money(row.paid_amount) }
])

async function load() {
  errorMessage.value = ''
  try {
    record.value = await getCortexApiClient().getCustomer(String(route.params.customer))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

function openInsurance() {
  insuranceDate.value = record.value?.insurance.valid_until ?? ''
  insuranceNote.value = ''
  insuranceError.value = ''
  insuranceOpen.value = true
}

async function saveInsurance() {
  savingInsurance.value = true
  insuranceError.value = ''
  try {
    record.value = await getCortexApiClient().setCustomerInsurance(record.value!.name, insuranceDate.value || null, insuranceNote.value || undefined)
    toast.create({ message: t('customers.insurance_saved'), type: 'success' })
    insuranceOpen.value = false
  } catch (error) {
    insuranceError.value = error instanceof Error ? error.message : String(error)
  } finally {
    savingInsurance.value = false
  }
}

watch(() => route.params.customer, () => void load())
onMounted(load)
</script>
