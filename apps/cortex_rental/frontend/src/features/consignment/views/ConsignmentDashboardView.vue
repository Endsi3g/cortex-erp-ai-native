<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.consignment_dashboard')">
      <template #title-suffix>
        <Tooltip v-if="dashboard?.provenance === 'mock'" :text="t('consignment_screen.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <TextInput v-model="period" type="month" size="sm" variant="subtle" class="w-40" :aria-label="t('consignment_screen.period')" />
        <Button size="sm" variant="subtle" :route="{ name: 'consignment-owners' }">{{ t('routes.consignment_owners') }}</Button>
      </template>
    </PageHeader>

    <p v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>
    <div v-else-if="!dashboard" class="mx-6 mt-10 flex items-center gap-2 text-base text-ink-gray-5" role="status"><LoadingIndicator class="size-4" /> {{ t('table.loading') }}</div>

    <template v-else>
      <section class="grid grid-cols-2 gap-4 px-6 pt-5 xl:grid-cols-4" :aria-label="t('consignment_screen.kpis')">
        <div v-for="card in cards" :key="card.label" class="rounded border border-outline-gray-1 px-4 py-3">
          <p class="text-base text-ink-gray-6">{{ card.label }}</p>
          <p class="mt-2 text-2xl font-semibold tabular-nums text-ink-gray-8">{{ card.value }}</p>
        </div>
      </section>

      <section class="mt-6">
        <h2 class="px-6 pb-2 text-base font-semibold text-ink-gray-9">{{ t('consignment_screen.owners_for', { period: periodLabel }) }}</h2>
        <DataTable :label="t('routes.consignment_owners')" :columns="ownerColumns" :rows="dashboard.owners" row-key="id" :filter-row="false" :empty-text="t('consignment_screen.no_owners')" clickable @row-click="row => openStatement(String(row.id))">
          <template #cell-statement_status="{ row }"><StatementStatusBadge :status="row.statement_status as StatementStatus" /></template>
        </DataTable>
      </section>

      <section class="mt-6 pb-8">
        <h2 class="px-6 pb-2 text-base font-semibold text-ink-gray-9">{{ t('consignment_screen.top_units') }}</h2>
        <DataTable :label="t('consignment_screen.top_units')" :columns="itemColumns" :rows="topItems" row-key="serial_number" :filter-row="false" :empty-text="t('consignment_screen.no_revenue')" />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, LoadingIndicator, TextInput, Tooltip } from 'frappe-ui'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { ConsignmentDashboardResponse, ConsignmentOwner, StatementStatus } from '@/api/contracts'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import StatementStatusBadge from '../components/StatementStatusBadge.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const currentMonth = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}` }
const period = ref(typeof route.query.period === 'string' ? route.query.period : currentMonth())
const dashboard = ref<ConsignmentDashboardResponse | null>(null)
const errorMessage = ref('')

const money = (value: number) => formatMoney(value, dashboard.value?.currency, locale.value as LocaleType)
const periodLabel = computed(() => new Intl.DateTimeFormat(locale.value, { month: 'long', year: 'numeric' }).format(new Date(`${period.value}-01T00:00:00`)))

const cards = computed(() => {
  const d = dashboard.value!
  return [
    { label: t('consignment_screen.due_this_period'), value: money(d.current_month_total_payout) },
    { label: t('consignment_screen.due_previous_period'), value: money(d.previous_month_total_payout) },
    { label: t('consignment_screen.active_owners'), value: String(d.active_owners_count) },
    { label: t('consignment_screen.consigned_units'), value: String(d.active_consigned_serials_count) }
  ]
})

const ownerColumns = computed<DataTableColumn<ConsignmentOwner>[]>(() => [
  { key: 'display_name', label: t('consignment_screen.owner'), width: '260px' },
  { key: 'owner_code', label: t('catalog.code'), width: '110px' },
  { key: 'default_commission_percentage', label: t('consignment_screen.share'), width: '100px', align: 'right', format: row => `${row.default_commission_percentage} %` },
  { key: 'active_serials_count', label: t('consignment_screen.units'), width: '90px', align: 'right' },
  { key: 'period_revenue', label: t('consignment_screen.revenue'), width: '150px', align: 'right', format: row => money(row.period_revenue) },
  { key: 'period_amount_due', label: t('consignment_screen.amount_due'), width: '150px', align: 'right', format: row => money(row.period_amount_due) },
  { key: 'statement_status', label: t('consignment_screen.statement'), width: '150px' }
])

type ItemRow = ConsignmentDashboardResponse['top_earning_items'][number] & Record<string, unknown>
const topItems = computed(() => (dashboard.value?.top_earning_items ?? []) as ItemRow[])
const itemColumns = computed<DataTableColumn<ItemRow>[]>(() => [
  { key: 'serial_number', label: t('rental_detail.serial'), width: '200px' },
  { key: 'item_name', label: t('rental_detail.item'), width: '300px' },
  { key: 'owner_code', label: t('consignment_screen.owner'), width: '120px' },
  { key: 'revenue_generated', label: t('consignment_screen.revenue'), width: '150px', align: 'right', format: row => money(row.revenue_generated) },
  { key: 'owner_payout', label: t('consignment_screen.amount_due'), width: '150px', align: 'right', format: row => money(row.owner_payout) }
])

function openStatement(ownerId: string) {
  void router.push({ name: 'owner-statement', params: { owner: ownerId, period: period.value } })
}

async function load() {
  errorMessage.value = ''
  try {
    dashboard.value = await getCortexApiClient().getConsignmentDashboard({ period: period.value })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

watch(period, value => {
  void router.replace({ query: { period: value } })
  void load()
})
onMounted(load)
</script>
