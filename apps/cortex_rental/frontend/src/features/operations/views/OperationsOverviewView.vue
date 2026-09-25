<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.operations_overview')">
      <template #title-suffix>
        <Tooltip v-if="overview?.provenance === 'mock'" :text="t('operations.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <TextInput v-model="day" type="date" size="sm" variant="subtle" class="w-40" :aria-label="t('operations.day')" />
        <Tooltip :text="t('finance.pnl.refresh')">
          <Button size="sm" variant="subtle" class="w-8" :aria-label="t('finance.pnl.refresh')" :loading="loading" @click="load">
            <template #icon><RefreshCw class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Tooltip>
      </template>
    </PageHeader>

    <div v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-3" role="alert">
      <p class="text-base font-medium text-ink-red-4">{{ t('operations.load_failed') }}</p>
      <p class="mt-1 text-p-sm text-ink-gray-7">{{ errorMessage }}</p>
    </div>
    <div v-else-if="loading && !overview" class="mx-6 mt-10 flex items-center gap-2 text-base text-ink-gray-5" role="status">
      <LoadingIndicator class="size-4" /> {{ t('operations.loading') }}
    </div>

    <template v-else-if="overview">
      <!-- Number cards -->
      <section class="grid grid-cols-2 gap-4 px-6 pt-5 md:grid-cols-3 xl:grid-cols-6" :aria-label="t('operations.kpis')">
        <component
          :is="card.to ? RouterLink : 'button'"
          v-for="card in cards"
          :key="card.key"
          v-bind="card.to ? { to: card.to } : { type: 'button' }"
          class="rounded border px-4 py-3 text-left outline-none transition-colors hover:bg-surface-gray-1 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          :class="focus === card.key ? 'border-outline-gray-4' : 'border-outline-gray-1'"
          :aria-pressed="card.to ? undefined : focus === card.key"
          @click="!card.to && (focus = focus === card.key ? 'all' : (card.key as Focus))"
        >
          <p class="text-base text-ink-gray-6">{{ card.label }}</p>
          <p class="mt-2 text-2xl font-semibold tabular-nums" :class="card.alert && card.value > 0 ? 'text-ink-red-4' : 'text-ink-gray-8'">{{ card.value }}</p>
        </component>
      </section>

      <!-- To handle -->
      <section v-if="attention.length && (focus === 'all' || focus === 'overdue' || focus === 'exceptions')" class="mt-6">
        <h2 class="px-6 pb-2 text-base font-semibold text-ink-gray-9">{{ t('operations.attention') }}</h2>
        <DataTable :label="t('operations.attention')" :columns="attentionColumns" :rows="attention" row-key="key" :filter-row="false" clickable @row-click="row => router.push(row.to)">
          <template #cell-kind="{ row }">
            <Badge :theme="row.severity" variant="subtle">{{ row.kind }}</Badge>
          </template>
        </DataTable>
      </section>

      <section v-if="focus === 'all' || focus === 'departures'" class="mt-6">
        <h2 class="px-6 pb-2 text-base font-semibold text-ink-gray-9">{{ t('operations.departures') }}</h2>
        <DataTable :label="t('operations.departures')" :columns="rentalColumns('starts_at')" :rows="departures" :filter-row="false" :empty-text="t('operations.no_departures')" clickable @row-click="row => openRental(String(row.name))">
          <template #cell-rental_state="{ row }"><RentalStateBadge :state="row.rental_state as RentalStateValue" /></template>
          <template #cell-missing="{ row }">
            <span v-if="(row.missing_requirements as string[]).length" class="text-ink-amber-3">{{ missingLabel(row.missing_requirements as string[]) }}</span>
            <span v-else class="text-ink-green-3">{{ t('rentals.ready') }}</span>
          </template>
        </DataTable>
      </section>

      <section v-if="focus === 'all' || focus === 'returns'" class="mt-6 pb-8">
        <h2 class="px-6 pb-2 text-base font-semibold text-ink-gray-9">{{ t('operations.returns') }}</h2>
        <DataTable :label="t('operations.returns')" :columns="rentalColumns('ends_at')" :rows="returns" :filter-row="false" :empty-text="t('operations.no_returns')" clickable @row-click="row => openRental(String(row.name))">
          <template #cell-rental_state="{ row }"><RentalStateBadge :state="row.rental_state as RentalStateValue" /></template>
          <template #cell-missing>—</template>
        </DataTable>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, LoadingIndicator, TextInput, Tooltip } from 'frappe-ui'
import { RefreshCw } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { OperationsOverview, OperationsRow, RentalStateValue } from '@/api/contracts/rentals'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'
import RentalStateBadge from '@/features/rentals/components/RentalStateBadge.vue'

type Focus = 'all' | 'departures' | 'returns' | 'overdue' | 'exceptions'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const localToday = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}
const day = ref(typeof route.query.day === 'string' ? route.query.day : localToday())
const focus = ref<Focus>('all')
const overview = ref<OperationsOverview | null>(null)
const loading = ref(false)
const errorMessage = ref('')

const loc = () => locale.value as LocaleType

const cards = computed(() => {
  const k = overview.value?.kpis
  if (!k) return []
  return [
    { key: 'departures', label: t('operations.kpi_departures'), value: k.departures },
    { key: 'returns', label: t('operations.kpi_returns'), value: k.returns },
    { key: 'overdue', label: t('operations.kpi_overdue'), value: k.overdue, alert: true },
    { key: 'exceptions', label: t('operations.kpi_exceptions'), value: k.exceptions, alert: true },
    ...(session.hasPermission('cortex:approvals:decide')
      ? [{ key: 'approvals', label: t('operations.kpi_approvals'), value: k.approvals_pending, to: { name: 'ai-inbox', query: { type: 'approval' } } }]
      : []),
    ...(session.hasPermission('cortex:intake:view')
      ? [{ key: 'inbound', label: t('operations.kpi_inbound'), value: k.inbound_pending, to: { name: 'ai-inbox', query: { type: 'inbound' } } }]
      : [])
  ] as Array<{ key: Focus | 'approvals' | 'inbound'; label: string; value: number; alert?: boolean; to?: object }>
})

type Row = OperationsRow & Record<string, unknown>
const departures = computed(() => (overview.value?.departures ?? []) as Row[])
const returns = computed(() => (overview.value?.returns ?? []) as Row[])

function rentalColumns(timeKey: 'starts_at' | 'ends_at'): DataTableColumn<Row>[] {
  return [
    { key: timeKey, label: timeKey === 'starts_at' ? t('rentals.col_start') : t('rentals.col_end'), width: '170px', format: row => formatDateTime(String(row[timeKey]), loc()) },
    { key: 'name', label: t('rentals.col_id'), width: '170px' },
    { key: 'customer_name', label: t('rentals.col_customer'), width: '240px' },
    { key: 'project_name', label: t('rentals.col_project'), width: '200px' },
    { key: 'rental_state', label: t('rentals.col_state'), width: '120px' },
    { key: 'missing', label: t('rentals.col_ready'), width: '260px', sortable: false }
  ]
}

const REQUIREMENT_LABEL: Record<string, string> = {
  customer_account_ready: 'rental_detail.readiness.account',
  insurance_ready: 'rental_detail.readiness.insurance',
  payment_ready: 'rental_detail.readiness.payment'
}
const missingLabel = (keys: string[]) => keys.map(key => t(REQUIREMENT_LABEL[key])).join(', ')

interface AttentionRow extends Record<string, unknown> { key: string; kind: string; severity: 'red' | 'orange'; reference: string; detail: string; to: object }
const attention = computed<AttentionRow[]>(() => {
  const o = overview.value
  if (!o) return []
  return [
    ...o.overdue.map(r => ({ key: `overdue:${r.name}`, kind: t('operations.kind_overdue'), severity: 'red' as const, reference: r.name, detail: `${r.customer_name} · ${t('operations.due')} ${formatDateTime(r.ends_at, loc())}`, to: { name: 'rental-detail', params: { name: r.name } } })),
    ...o.at_risk.map(r => ({ key: `risk:${r.name}`, kind: t('operations.kind_requirements'), severity: 'orange' as const, reference: r.name, detail: `${r.customer_name} · ${missingLabel(r.missing_requirements)}`, to: { name: 'rental-detail', params: { name: r.name } } })),
    ...o.exceptions.map(r => ({ key: `exception:${r.name}`, kind: t(`rental_states.${r.rental_state}`), severity: 'red' as const, reference: r.name, detail: r.customer_name, to: { name: 'rental-detail', params: { name: r.name } } })),
    ...o.serials_out_of_service.map(s => ({ key: `serial:${s.serial_no}`, kind: t('operations.kind_serial'), severity: 'orange' as const, reference: s.serial_no, detail: `${s.item_code} · ${s.status}`, to: { name: 'serial-detail', params: { serial: s.serial_no } } }))
  ]
})
const attentionColumns = computed<DataTableColumn<AttentionRow>[]>(() => [
  { key: 'kind', label: t('operations.col_kind'), width: '200px' },
  { key: 'reference', label: t('operations.col_reference'), width: '190px' },
  { key: 'detail', label: t('operations.col_detail'), width: '520px' }
])

function openRental(name: string) {
  void router.push({ name: 'rental-detail', params: { name } })
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    overview.value = await getCortexApiClient().getOperationsOverview(day.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

watch(day, value => {
  void router.replace({ query: value === localToday() ? {} : { day: value } })
  void load()
})
onMounted(load)
</script>
