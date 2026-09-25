<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="record?.serial_no || String(route.params.serial)">
      <template #title-suffix>
        <SerialStatusBadge v-if="record" :status="record.status" size="md" />
        <Tooltip v-if="record?.provenance === 'mock'" :text="t('catalog.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template v-if="record" #actions>
        <Button size="sm" variant="subtle" class="print:hidden" @click="printLabel">{{ t('catalog.print_label') }}</Button>
        <Dropdown v-if="record.can_change_status && statusActions.length" :options="statusActions" align="end">
          <Button size="sm" variant="solid" class="print:hidden">
            {{ t('catalog.change_status') }}
            <template #suffix><ChevronDown class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Dropdown>
      </template>
    </PageHeader>

    <p v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>
    <div v-else-if="!record" class="mx-6 mt-10 flex items-center gap-2 text-base text-ink-gray-5" role="status"><LoadingIndicator class="size-4" /> {{ t('table.loading') }}</div>

    <template v-else>
      <!-- Printable label: only this block prints -->
      <div class="hidden print:block print:p-8">
        <p class="text-3xl font-semibold">{{ record.serial_no }}</p>
        <p class="mt-2 text-xl">{{ record.item_name }}</p>
        <p class="mt-1 text-lg">{{ record.item_code }}</p>
      </div>

      <dl class="grid grid-cols-2 gap-x-8 gap-y-4 border-b border-outline-gray-1 px-6 py-5 md:grid-cols-4 print:hidden">
        <div class="col-span-2 md:col-span-1">
          <dt class="text-sm text-ink-gray-5">{{ t('rental_detail.item') }}</dt>
          <dd class="mt-1 text-base"><RouterLink :to="{ name: 'equipment-detail', params: { item: record.item_code } }" class="hover:underline">{{ record.item_name }}</RouterLink></dd>
        </div>
        <div>
          <dt class="text-sm text-ink-gray-5">{{ t('catalog.current_rental') }}</dt>
          <dd class="mt-1 text-base">
            <RouterLink v-if="record.current_rental" :to="{ name: 'rental-detail', params: { name: record.current_rental } }" class="underline decoration-outline-gray-3 underline-offset-2">{{ record.current_rental }}</RouterLink>
            <span v-else class="text-ink-gray-5">{{ t('catalog.in_stock') }}</span>
          </dd>
        </div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('catalog.erpnext_status') }}</dt><dd class="mt-1 text-base">{{ record.erpnext_status || '—' }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('catalog.warranty') }}</dt><dd class="mt-1 text-base">{{ record.warranty_expiry_date ? date(record.warranty_expiry_date) : '—' }}</dd></div>
      </dl>

      <section class="mt-5 print:hidden">
        <h2 class="px-6 pb-2 text-base font-semibold text-ink-gray-9">{{ t('catalog.rental_history') }}</h2>
        <DataTable :label="t('catalog.rental_history')" :columns="rentalColumns" :rows="rentalRows" row-key="name" :filter-row="false" :empty-text="t('catalog.no_rentals')" clickable @row-click="row => router.push({ name: 'rental-detail', params: { name: String(row.name) } })">
          <template #cell-rental_state="{ row }"><RentalStateBadge :state="row.rental_state as RentalStateValue" /></template>
        </DataTable>
      </section>

      <section class="mt-6 print:hidden">
        <h2 class="px-6 pb-2 text-base font-semibold text-ink-gray-9">{{ t('catalog.return_history') }}</h2>
        <DataTable :label="t('catalog.return_history')" :columns="returnColumns" :rows="returnRows" row-key="checkin" :filter-row="false" :empty-text="t('catalog.no_returns')" />
      </section>

      <section class="mt-6 pb-8 print:hidden">
        <h2 class="px-6 pb-2 text-base font-semibold text-ink-gray-9">{{ t('catalog.status_history') }}</h2>
        <DataTable :label="t('catalog.status_history')" :columns="historyColumns" :rows="historyRows" row-key="id" :filter-row="false" :empty-text="t('catalog.no_status_changes')" />
      </section>
    </template>

    <ReasonDialog
      v-model="statusOpen"
      :title="pendingStatus ? t('catalog.status_to', { status: t(`catalog.serial_status.${pendingStatus.replace(/ /g, '_')}`) }) : ''"
      :label="t('catalog.status_reason')"
      :confirm-label="t('catalog.confirm_status')"
      :cancel-label="t('common.cancel')"
      :loading="saving"
      :error="statusError"
      :danger="pendingStatus === 'Missing' || pendingStatus === 'Decommissioned'"
      @confirm="applyStatus"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dropdown, LoadingIndicator, Tooltip, toast } from 'frappe-ui'
import { ChevronDown } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import ReasonDialog from '@/design-system/components/page/ReasonDialog.vue'
import { getCortexApiClient } from '@/api'
import type { SerialRecord, SerialStatus } from '@/api/contracts/catalog'
import type { RentalStateValue } from '@/api/contracts/rentals'
import { formatDate, formatDateTime, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'
import RentalStateBadge from '@/features/rentals/components/RentalStateBadge.vue'
import SerialStatusBadge from '../components/SerialStatusBadge.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const record = ref<SerialRecord | null>(null)
const errorMessage = ref('')
const statusOpen = ref(false)
const pendingStatus = ref<SerialStatus | null>(null)
const saving = ref(false)
const statusError = ref('')

const loc = () => locale.value as LocaleType
const date = (value: string) => formatDate(value, loc())
const dateTime = (value: string) => formatDateTime(value, loc())

const STATUSES: SerialStatus[] = ['Active', 'Quarantine', 'Under Repair', 'Missing', 'Decommissioned']
const statusActions = computed(() =>
  STATUSES.filter(status => status !== record.value?.status && (!record.value?.current_rental || status === 'Missing')).map(status => ({
    label: t(`catalog.status_action.${status.replace(/ /g, '_')}`),
    theme: status === 'Missing' || status === 'Decommissioned' ? 'red' : undefined,
    onClick: () => {
      pendingStatus.value = status
      statusError.value = ''
      statusOpen.value = true
    }
  }))
)

type RentalRow = SerialRecord['rentals'][number] & Record<string, unknown>
type ReturnRow = SerialRecord['returns'][number] & Record<string, unknown>
type HistoryRow = SerialRecord['status_history'][number] & Record<string, unknown>
const rentalRows = computed(() => (record.value?.rentals ?? []) as RentalRow[])
const returnRows = computed(() => (record.value?.returns ?? []) as ReturnRow[])
const historyRows = computed(() => (record.value?.status_history ?? []) as HistoryRow[])

const rentalColumns = computed<DataTableColumn<RentalRow>[]>(() => [
  { key: 'name', label: t('rentals.col_id'), width: '170px' },
  { key: 'customer', label: t('rentals.col_customer'), width: '240px' },
  { key: 'rental_state', label: t('rentals.col_state'), width: '130px' },
  { key: 'starts_at', label: t('rentals.col_start'), width: '180px', format: row => dateTime(row.starts_at) },
  { key: 'ends_at', label: t('rentals.col_end'), width: '180px', format: row => dateTime(row.ends_at) }
])
const returnColumns = computed<DataTableColumn<ReturnRow>[]>(() => [
  { key: 'checked_in_at', label: t('finance.invoices.date'), width: '170px', format: row => (row.checked_in_at ? dateTime(row.checked_in_at) : '') },
  { key: 'transaction', label: t('rentals.col_id'), width: '170px' },
  { key: 'condition', label: t('warehouse.condition'), width: '130px', format: row => t(`warehouse.condition_${row.condition}`) },
  { key: 'disposition', label: t('warehouse.disposition'), width: '150px' },
  { key: 'damage_type', label: t('warehouse.damage_type'), width: '170px', format: row => (row.damage_type === 'None' ? '' : row.damage_type) },
  { key: 'estimated_repair_cost', label: t('warehouse.repair_cost'), width: '150px', align: 'right', format: row => (row.estimated_repair_cost ? formatMoney(row.estimated_repair_cost, session.activeCompany?.currency, loc()) : '') },
  { key: 'notes', label: t('warehouse.damage_notes'), width: '260px' }
])
const historyColumns = computed<DataTableColumn<HistoryRow>[]>(() => [
  { key: 'timestamp', label: t('finance.invoices.date'), width: '180px', format: row => dateTime(row.timestamp) },
  { key: 'actor', label: t('rental_detail.actor'), width: '220px' },
  { key: 'detail', label: t('rental_detail.change'), width: '460px' }
])

async function load() {
  errorMessage.value = ''
  try {
    record.value = await getCortexApiClient().getSerial({ serial_number: String(route.params.serial) })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

async function applyStatus(reason: string) {
  if (!pendingStatus.value || !record.value) return
  saving.value = true
  statusError.value = ''
  try {
    record.value = await getCortexApiClient().setSerialStatus(record.value.serial_no, pendingStatus.value, reason)
    toast.create({ message: t('catalog.status_saved'), type: 'success' })
    statusOpen.value = false
  } catch (error) {
    statusError.value = error instanceof Error ? error.message : String(error)
  } finally {
    saving.value = false
  }
}

function printLabel() {
  window.print()
}

watch(() => route.params.serial, () => void load())
onMounted(load)
</script>
