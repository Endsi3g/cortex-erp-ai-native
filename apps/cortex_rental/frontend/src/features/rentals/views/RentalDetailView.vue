<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="rental?.name || String(route.params.name)">
      <template #title-suffix>
        <RentalStateBadge v-if="rental" :state="rental.rental_state" size="md" />
        <Tooltip v-if="rental?.provenance === 'demo' || rental?.provenance === 'mock'" :text="t('rentals.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template v-if="rental" #actions>
        <Dropdown v-if="secondaryActions.length" :options="secondaryActions" align="end">
          <Button size="sm" variant="subtle" class="w-8" :aria-label="t('rental_detail.more_actions')">
            <template #icon><Ellipsis class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Dropdown>
        <Button v-if="primaryAction" size="sm" variant="solid" :loading="acting" @click="primaryAction.run">
          {{ primaryAction.label }}
        </Button>
      </template>
    </PageHeader>

    <div v-if="loading && !rental" class="mx-6 mt-10 flex items-center gap-2 text-base text-ink-gray-5" role="status">
      <LoadingIndicator class="size-4" /> {{ t('rental_detail.loading') }}
    </div>
    <div v-else-if="errorMessage && !rental" class="mx-6 mt-10 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-3" role="alert">
      <p class="text-base font-medium text-ink-red-4">{{ t('rental_detail.load_failed') }}</p>
      <p class="mt-1 text-p-sm text-ink-gray-7">{{ errorMessage }}</p>
    </div>

    <template v-else-if="rental">
      <p v-if="actionError" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">
        {{ actionError }}
      </p>

      <!-- Summary strip (ERPNext form header fields) -->
      <dl class="grid grid-cols-2 gap-x-8 gap-y-4 border-b border-outline-gray-1 px-6 py-5 md:grid-cols-3 xl:grid-cols-6">
        <div class="col-span-2 md:col-span-1 xl:col-span-2">
          <dt class="text-sm text-ink-gray-5">{{ t('rentals.col_customer') }}</dt>
          <dd class="mt-1 truncate text-base text-ink-gray-9">
            <RouterLink :to="{ name: 'customer-detail', params: { customer: rental.customer_id } }" class="hover:underline">{{ rental.customer_name }}</RouterLink>
          </dd>
        </div>
        <div>
          <dt class="text-sm text-ink-gray-5">{{ t('rentals.col_project') }}</dt>
          <dd class="mt-1 truncate text-base text-ink-gray-8">{{ rental.project_name || '—' }}</dd>
        </div>
        <div>
          <dt class="text-sm text-ink-gray-5">{{ t('rental_detail.period') }}</dt>
          <dd class="mt-1 text-base text-ink-gray-8">{{ dateTime(rental.starts_at) }} → {{ dateTime(rental.ends_at) }}</dd>
        </div>
        <div>
          <dt class="text-sm text-ink-gray-5">{{ t('rental_detail.days') }}</dt>
          <dd class="mt-1 text-base text-ink-gray-8">{{ t('rental_detail.days_value', { calendar: rental.calendar_days, billable: rental.billable_days }) }}</dd>
        </div>
        <div>
          <dt class="text-sm text-ink-gray-5">{{ t('rentals.col_total') }}</dt>
          <dd class="mt-1 text-base font-semibold tabular-nums text-ink-gray-9">{{ money(rental.grand_total) }}</dd>
        </div>
      </dl>

      <div class="grid grid-cols-1 gap-6 px-6 py-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div class="min-w-0">
          <TabButtons v-model="tab" :buttons="tabs" class="mb-4" />

          <!-- Overview: lines and totals -->
          <section v-if="tab === 'overview'" class="space-y-4">
            <DataTable :label="t('rental_detail.lines')" :columns="lineColumns" :rows="lineRows" row-key="id" :filter-row="false" />
            <dl class="ml-auto w-full max-w-sm space-y-1.5 text-base">
              <div class="flex justify-between"><dt class="text-ink-gray-6">{{ t('rental_detail.subtotal') }}</dt><dd class="tabular-nums">{{ money(rental.subtotal) }}</dd></div>
              <div v-if="rental.discount_total" class="flex justify-between"><dt class="text-ink-gray-6">{{ t('rental_detail.discounts') }}</dt><dd class="tabular-nums">− {{ money(rental.discount_total) }}</dd></div>
              <div class="flex justify-between">
                <dt class="text-ink-gray-6">{{ rental.erpnext_sales_order ? t('rental_detail.taxes_erpnext') : t('rental_detail.taxes_estimated') }}</dt>
                <dd class="tabular-nums">{{ money(rental.tax_amount) }}</dd>
              </div>
              <div class="flex justify-between border-t border-outline-gray-1 pt-1.5 font-semibold text-ink-gray-9"><dt>{{ t('rentals.col_total') }}</dt><dd class="tabular-nums">{{ money(rental.grand_total) }}</dd></div>
            </dl>
            <p v-if="rental.notes" class="rounded bg-surface-gray-1 px-3 py-2 text-p-sm text-ink-gray-7">{{ rental.notes }}</p>
          </section>

          <RentalBillingPanel v-else-if="tab === 'billing'" :rental="rental" @changed="load" />

          <!-- Equipment & serials -->
          <section v-else-if="tab === 'equipment'">
            <DataTable :label="t('rental_detail.tabs.equipment')" :columns="serialColumns" :rows="serialRows" row-key="key" :filter-row="false" :empty-text="t('rental_detail.no_serials')">
              <template #cell-status="{ row }">
                <Badge :theme="row.status === 'in' ? 'green' : row.status === 'out' ? 'orange' : 'gray'" variant="subtle">{{ t(`rental_detail.serial_${row.status}`) }}</Badge>
              </template>
            </DataTable>
          </section>

          <!-- Audit -->
          <section v-else-if="tab === 'audit'">
            <DataTable :label="t('rental_detail.tabs.audit')" :columns="auditColumns" :rows="auditRows" row-key="id" :loading="auditLoading" :filter-row="false" :empty-text="t('rental_detail.no_audit')" />
          </section>
        </div>

        <aside class="space-y-4">
          <RentalReadinessPanel :rental="rental" @updated="value => (rental = value)" />
          <section v-if="rental.erpnext_sales_order" class="rounded border border-outline-gray-1 px-4 py-3 text-base">
            <h2 class="font-semibold text-ink-gray-9">{{ t('rental_detail.erpnext_documents') }}</h2>
            <ul class="mt-2 space-y-1 text-ink-gray-7">
              <li>{{ t('rental_detail.billing.sales_order') }} : <a :href="`/app/sales-order/${encodeURIComponent(rental.erpnext_sales_order)}`" target="_blank" rel="noopener" class="underline decoration-outline-gray-3 underline-offset-2">{{ rental.erpnext_sales_order }}</a></li>
              <li v-if="rental.final_invoice">{{ t('rental_detail.billing.final_invoice') }} : <a :href="`/app/sales-invoice/${encodeURIComponent(rental.final_invoice)}`" target="_blank" rel="noopener" class="underline decoration-outline-gray-3 underline-offset-2">{{ rental.final_invoice }}</a></li>
            </ul>
          </section>
        </aside>
      </div>
    </template>

    <ReasonDialog
      v-model="cancelOpen"
      :title="t('rental_detail.cancel_title')"
      :description="t('rental_detail.cancel_description')"
      :label="t('rental_detail.cancel_reason')"
      :confirm-label="t('rental_detail.actions.cancel')"
      :cancel-label="t('common.cancel')"
      :loading="acting"
      :error="actionError"
      danger
      @confirm="cancelRental"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dropdown, LoadingIndicator, TabButtons, Tooltip, toast } from 'frappe-ui'
import { Ellipsis } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import ReasonDialog from '@/design-system/components/page/ReasonDialog.vue'
import { getCortexApiClient } from '@/api'
import type { GetRentalAuditResponse, GetRentalResponse, RentalAction } from '@/api/contracts'
import { formatDateTime, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import RentalStateBadge from '../components/RentalStateBadge.vue'
import RentalReadinessPanel from '../components/detail/RentalReadinessPanel.vue'
import RentalBillingPanel from '../components/detail/RentalBillingPanel.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const rental = ref<GetRentalResponse | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const acting = ref(false)
const actionError = ref('')
const cancelOpen = ref(false)
const tab = ref<'overview' | 'billing' | 'equipment' | 'audit'>(
  (['billing', 'equipment', 'audit'] as const).find(value => value === route.query.tab) ?? 'overview'
)
const audit = ref<GetRentalAuditResponse | null>(null)
const auditLoading = ref(false)

const loc = () => locale.value as LocaleType
const money = (value: number | undefined) => formatMoney(value ?? 0, rental.value?.currency, loc())
const dateTime = (value: string) => formatDateTime(value, loc())

const tabs = computed(() => [
  { label: t('rental_detail.tabs.overview'), value: 'overview' },
  { label: t('rental_detail.tabs.billing'), value: 'billing' },
  { label: t('rental_detail.tabs.equipment'), value: 'equipment' },
  { label: t('rental_detail.tabs.audit'), value: 'audit' }
])

// ---- data -------------------------------------------------------------------
async function load() {
  const name = String(route.params.name)
  loading.value = true
  errorMessage.value = ''
  try {
    rental.value = await getCortexApiClient().getRental({ id: name })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function loadAudit() {
  if (!rental.value) return
  auditLoading.value = true
  try {
    audit.value = await getCortexApiClient().getRentalAudit({ rental_id: rental.value.id })
  } catch {
    audit.value = null
  } finally {
    auditLoading.value = false
  }
}

watch(tab, value => {
  void router.replace({ query: value === 'overview' ? {} : { tab: value } })
  if (value === 'audit') void loadAudit()
})
watch(() => route.params.name, () => void load())
onMounted(async () => {
  await load()
  if (tab.value === 'audit') await loadAudit()
})

// ---- tables -----------------------------------------------------------------
type Line = GetRentalResponse['items'][number] & Record<string, unknown>
const lineRows = computed(() => (rental.value?.items ?? []) as Line[])
const lineColumns = computed<DataTableColumn<Line>[]>(() => [
  { key: 'item_name', label: t('rental_detail.item'), format: row => `${row.item_name} · ${row.item_code}` },
  { key: 'quantity', label: t('rental_detail.qty'), width: '80px', align: 'right' },
  { key: 'daily_rate', label: t('rental_detail.daily_rate'), width: '130px', align: 'right', format: row => money(row.daily_rate) },
  { key: 'discount_percentage', label: t('rental_detail.discount'), width: '90px', align: 'right', format: row => (row.discount_percentage ? `${row.discount_percentage} %` : '') },
  { key: 'billable_days', label: t('rentals.col_billable_days'), width: '110px', align: 'right' },
  { key: 'subtotal', label: t('rental_detail.amount'), width: '140px', align: 'right', format: row => money(row.subtotal) }
])

interface SerialRow extends Record<string, unknown> { key: string; item: string; serial: string; status: 'assigned' | 'out' | 'in' }
const serialRows = computed<SerialRow[]>(() =>
  (rental.value?.items ?? []).flatMap(line =>
    line.assigned_serials.map(serial => ({
      key: `${line.id}:${serial}`,
      item: `${line.item_name} · ${line.item_code}`,
      serial,
      status: line.scanned_checkin_serials.includes(serial) ? 'in' : line.scanned_checkout_serials.includes(serial) ? 'out' : 'assigned'
    }))
  )
)
const serialColumns = computed<DataTableColumn<SerialRow>[]>(() => [
  { key: 'item', label: t('rental_detail.item'), width: '320px' },
  { key: 'serial', label: t('rental_detail.serial'), width: '200px' },
  { key: 'status', label: t('finance.invoices.state'), width: '160px' }
])

type AuditRow = GetRentalAuditResponse['events'][number] & Record<string, unknown>
const auditRows = computed(() => (audit.value?.events ?? []) as AuditRow[])
const auditColumns = computed<DataTableColumn<AuditRow>[]>(() => [
  { key: 'timestamp', label: t('finance.invoices.date'), width: '180px', format: row => dateTime(row.timestamp) },
  { key: 'actor', label: t('rental_detail.actor'), width: '220px', format: row => `${row.actor.actor_id} (${row.actor.actor_type})` },
  { key: 'action', label: t('rental_detail.action'), width: '320px' },
  { key: 'diff_summary', label: t('rental_detail.change'), width: '360px', format: row => row.diff_summary ?? '' }
])

// ---- actions (only those the server listed) ---------------------------------
async function run(task: () => Promise<unknown>, success: string) {
  acting.value = true
  actionError.value = ''
  try {
    await task()
    toast.create({ message: success, type: 'success' })
    await load()
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : String(error)
  } finally {
    acting.value = false
  }
}

async function confirmReservation() {
  const r = rental.value!
  await run(async () => {
    const result = await getCortexApiClient().requestReservation({ rental_id: r.id, version: r.version })
    if (result.status !== 'completed') throw new Error(result.errors?.[0]?.message ?? t('rental_detail.action_refused'))
  }, t('rental_detail.reserved'))
}

async function requestContract() {
  const r = rental.value!
  await run(async () => {
    const result = await getCortexApiClient().requestContractApproval({ rental_id: r.id, version: r.version })
    if (result.status === 'stale' || result.status === 'failed') throw new Error(result.errors?.[0]?.message ?? t('rental_detail.action_refused'))
  }, t('rental_detail.contract_requested'))
}

async function cancelRental(reason: string) {
  await run(async () => {
    await getCortexApiClient().cancelRental(rental.value!.id, reason)
    cancelOpen.value = false
  }, t('rental_detail.cancelled'))
}

const ACTIONS = computed<Partial<Record<RentalAction, { label: string; run: () => void }>>>(() => ({
  confirm_reservation: { label: t('rental_detail.actions.confirm_reservation'), run: confirmReservation },
  request_contract: { label: t('rental_detail.actions.request_contract'), run: requestContract },
  checkout: { label: t('rental_detail.actions.checkout'), run: () => router.push({ name: 'checkout-scanner', params: { rental: rental.value!.id } }) },
  checkin: { label: t('rental_detail.actions.checkin'), run: () => router.push({ name: 'checkin-scanner', params: { rental: rental.value!.id } }) },
  prepare_final_invoice: { label: t('rental_detail.actions.prepare_final_invoice'), run: () => (tab.value = 'billing') },
  record_advance: { label: t('rental_detail.actions.record_advance'), run: () => (tab.value = 'billing') },
  close: { label: t('rental_detail.actions.close'), run: () => run(() => getCortexApiClient().closeRental(rental.value!.id), t('rental_detail.closed')) },
  edit_quote: { label: t('rental_detail.actions.edit_quote'), run: () => router.push({ name: 'rental-composer', query: { rental: rental.value!.id } }) },
  cancel: { label: t('rental_detail.actions.cancel'), run: () => { actionError.value = ''; cancelOpen.value = true } }
}))

const PRIMARY_ORDER: RentalAction[] = ['confirm_reservation', 'request_contract', 'checkout', 'checkin', 'prepare_final_invoice', 'close']
const primaryKey = computed(() => PRIMARY_ORDER.find(action => rental.value?.available_actions.includes(action)))
const primaryAction = computed(() => (primaryKey.value ? ACTIONS.value[primaryKey.value] : undefined))

const secondaryActions = computed(() => {
  const r = rental.value
  if (!r) return []
  const items = r.available_actions
    .filter(action => action !== primaryKey.value && action !== 'verify_readiness' && ACTIONS.value[action])
    .map(action => ({ label: ACTIONS.value[action]!.label, onClick: ACTIONS.value[action]!.run, theme: action === 'cancel' ? 'red' : undefined }))
  items.push({ label: t('rental_detail.actions.open_in_erpnext'), onClick: () => window.open(`/app/cortex-rental-transaction/${encodeURIComponent(r.id)}`, '_blank', 'noopener'), theme: undefined })
  return items
})
</script>
