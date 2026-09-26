<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.rentals_list')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock'" :text="t('rentals.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Tooltip :text="t('finance.pnl.refresh')">
          <Button size="sm" variant="subtle" class="w-8" :aria-label="t('finance.pnl.refresh')" :loading="loading" @click="load">
            <template #icon><RefreshCw class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </Tooltip>
        <Button v-if="session.hasPermission('cortex:quote:create')" size="sm" variant="solid" :route="{ name: 'rental-composer' }">
          <template #prefix><Plus class="size-4" :stroke-width="1.5" /></template>
          {{ t('rentals.new_rental') }}
        </Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('rentals.filters')">
      <TextInput
        v-model="search"
        type="search"
        size="sm"
        variant="subtle"
        class="lg:col-span-2"
        :placeholder="t('rentals.search_placeholder')"
        :aria-label="t('rentals.search_placeholder')"
      />
      <Select
        :model-value="state"
        :options="stateOptions"
        :placeholder="t('rentals.col_state')"
        :aria-label="t('rentals.col_state')"
        @update:model-value="(value: unknown) => (state = value === ANY ? undefined : (value as RentalStateValue))"
      >
        <template #suffix><ChevronsUpDown class="ml-auto size-4 shrink-0 text-ink-gray-5" :stroke-width="1.5" /></template>
      </Select>
      <TextInput v-model="startsFrom" type="date" size="sm" variant="subtle" :aria-label="t('rentals.starts_from')" />
      <TextInput v-model="startsTo" type="date" size="sm" variant="subtle" :aria-label="t('rentals.starts_to')" />
    </PageFilters>

    <div v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-3" role="alert">
      <p class="text-base font-medium text-ink-red-4">{{ t('rentals.load_failed') }}</p>
      <p class="mt-1 text-p-sm text-ink-gray-7">{{ errorMessage }}</p>
    </div>

    <div class="mt-6">
      <DataTable
        :label="t('routes.rentals_list')"
        :columns="columns"
        :rows="rows"
        :loading="loading"
        :empty-text="t('rentals.empty')"
        :total="total"
        :page="page"
        :page-size="pageSize"
        clickable
        @row-click="row => router.push({ name: 'rental-detail', params: { name: String(row.name) } })"
        @update:page="value => (page = value)"
        @update:page-size="value => { pageSize = value; page = 1 }"
      >
        <template #cell-rental_state="{ row }">
          <RentalStateBadge :state="row.rental_state as RentalStateValue" />
        </template>
        <template #cell-ready="{ row }">
          <span class="inline-flex items-center gap-1.5" :class="row.ready ? 'text-ink-green-3' : 'text-ink-amber-3'">
            <span class="size-1.5 rounded-full" :class="row.ready ? 'bg-surface-green-3' : 'bg-surface-amber-3'" aria-hidden="true" />
            {{ row.ready ? t('rentals.ready') : t('rentals.not_ready') }}
          </span>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Select, TextInput, Tooltip } from 'frappe-ui'
import { ChevronsUpDown, Plus, RefreshCw } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { RentalStateValue, RentalSummary } from '@/api/contracts/rentals'
import { RentalStateSchema } from '@/api/contracts/rentals'
import { formatDateTime, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'
import RentalStateBadge from '../components/RentalStateBadge.vue'

const ANY = '__any__'
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const states = RentalStateSchema.options
const search = ref(typeof route.query.q === 'string' ? route.query.q : '')
const state = ref<RentalStateValue | undefined>(states.includes(route.query.state as RentalStateValue) ? (route.query.state as RentalStateValue) : undefined)
const startsFrom = ref(typeof route.query.from === 'string' ? route.query.from : '')
const startsTo = ref(typeof route.query.to === 'string' ? route.query.to : '')
const page = ref(1)
const pageSize = ref(20)

const rows = ref<RentalSummary[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const provenance = ref<'api' | 'mock' | undefined>()

const stateOptions = computed(() => [
  { label: `${t('rentals.col_state')} — ${t('finance.pnl.any')}`, value: ANY },
  ...states.map(value => ({ label: t(`rental_states.${value}`), value }))
])

const loc = () => locale.value as LocaleType
const columns = computed<DataTableColumn<RentalSummary>[]>(() => [
  { key: 'name', label: t('rentals.col_id'), width: '170px' },
  { key: 'customer_name', label: t('rentals.col_customer'), width: '220px' },
  { key: 'project_name', label: t('rentals.col_project'), width: '200px' },
  { key: 'rental_state', label: t('rentals.col_state'), width: '120px' },
  { key: 'starts_at', label: t('rentals.col_start'), width: '170px', format: row => formatDateTime(row.starts_at, loc()) },
  { key: 'ends_at', label: t('rentals.col_end'), width: '170px', format: row => formatDateTime(row.ends_at, loc()) },
  { key: 'billable_days', label: t('rentals.col_billable_days'), width: '110px', align: 'right', format: row => String(row.billable_days) },
  { key: 'grand_total', label: t('rentals.col_total'), width: '140px', align: 'right', format: row => formatMoney(row.grand_total, row.currency, loc()) },
  { key: 'ready', label: t('rentals.col_ready'), width: '130px' }
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().listRentalSummaries({
      page: page.value,
      page_size: pageSize.value,
      state: state.value,
      search: search.value || undefined,
      starts_from: startsFrom.value || undefined,
      starts_to: startsTo.value ? `${startsTo.value} 23:59:59` : undefined
    })
    rows.value = result.items
    total.value = result.total_count
    provenance.value = result.provenance
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch([search, state, startsFrom, startsTo], () => {
  page.value = 1
  void router.replace({ query: { q: search.value || undefined, state: state.value, from: startsFrom.value || undefined, to: startsTo.value || undefined } })
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})
watch([page, pageSize], () => void load())
onMounted(load)
</script>
