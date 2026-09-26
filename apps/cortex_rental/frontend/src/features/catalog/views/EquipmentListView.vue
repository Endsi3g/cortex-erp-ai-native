<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.equipment_list')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock'" :text="t('catalog.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" :route="{ name: 'kits-list' }">{{ t('routes.kits_list') }}</Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('catalog.filters')">
      <TextInput v-model="search" type="search" size="sm" variant="subtle" class="lg:col-span-2" :placeholder="t('catalog.search')" :aria-label="t('catalog.search')" />
      <Select
        :model-value="category"
        :options="categoryOptions"
        :placeholder="t('availability.category')"
        :aria-label="t('availability.category')"
        @update:model-value="(value: unknown) => (category = value === ANY ? undefined : String(value))"
      >
        <template #suffix><ChevronsUpDown class="ml-auto size-4 shrink-0 text-ink-gray-5" :stroke-width="1.5" /></template>
      </Select>
    </PageFilters>

    <p v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div class="mt-6">
      <DataTable
        :label="t('routes.equipment_list')"
        :columns="columns"
        :rows="rows"
        row-key="item_code"
        :loading="loading"
        :empty-text="t('catalog.empty')"
        :total="total"
        :page="page"
        :page-size="pageSize"
        clickable
        @row-click="row => router.push({ name: 'equipment-detail', params: { item: String(row.item_code) } })"
        @update:page="value => (page = value)"
        @update:page-size="value => { pageSize = value; page = 1 }"
      >
        <template #cell-fleet_unavailable="{ row }">
          <span :class="Number(row.fleet_unavailable) > 0 ? 'text-ink-amber-3' : ''">{{ row.fleet_unavailable }}</span>
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
import { ChevronsUpDown } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { EquipmentRow } from '@/api/contracts/catalog'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const ANY = '__any__'
const CATEGORIES = ['Camera Bodies', 'Cinema Lenses', 'Lighting', 'Grip & Rigging', 'Audio', 'Monitors & Wireless Video', 'Power & Batteries']

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const search = ref(typeof route.query.q === 'string' ? route.query.q : '')
const category = ref<string | undefined>(typeof route.query.category === 'string' ? route.query.category : undefined)
const page = ref(1)
const pageSize = ref(100)
const rows = ref<EquipmentRow[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const provenance = ref<string | undefined>()

const categoryOptions = computed(() => [{ label: `${t('availability.category')} — ${t('finance.pnl.any')}`, value: ANY }, ...CATEGORIES.map(value => ({ label: value, value }))])
const columns = computed<DataTableColumn<EquipmentRow>[]>(() => [
  { key: 'item_code', label: t('catalog.code'), width: '170px' },
  { key: 'item_name', label: t('catalog.name'), width: '320px' },
  { key: 'category', label: t('availability.category'), width: '190px' },
  { key: 'daily_rate', label: t('rental_detail.daily_rate'), width: '130px', align: 'right', format: row => formatMoney(row.daily_rate, row.currency, locale.value as LocaleType) },
  { key: 'fleet_total', label: t('catalog.fleet_total'), width: '90px', align: 'right' },
  { key: 'fleet_active', label: t('catalog.fleet_active'), width: '90px', align: 'right' },
  { key: 'fleet_out', label: t('catalog.fleet_out'), width: '90px', align: 'right' },
  { key: 'fleet_unavailable', label: t('catalog.fleet_unavailable'), width: '120px', align: 'right' }
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().listEquipment({ search: search.value || undefined, category: category.value, page: page.value, page_size: pageSize.value })
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
watch([search, category], () => {
  page.value = 1
  void router.replace({ query: { q: search.value || undefined, category: category.value } })
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})
watch([page, pageSize], () => void load())
onMounted(load)
</script>
