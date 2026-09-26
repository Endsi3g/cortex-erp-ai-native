<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="title" />
    <p class="px-6 pt-4 text-p-base text-ink-gray-6">{{ hint }}</p>
    <PageFilters :label="title">
      <TextInput v-model="search" type="search" size="sm" variant="subtle" class="lg:col-span-2" :placeholder="t('rentals.search_placeholder')" :aria-label="t('rentals.search_placeholder')" />
    </PageFilters>
    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>
    <div class="mt-6">
      <DataTable
        :label="title"
        :columns="columns"
        :rows="rows"
        :loading="loading"
        :empty-text="emptyText"
        :filter-row="false"
        clickable
        @row-click="row => $emit('pick', String(row.name))"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { TextInput } from 'frappe-ui'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { RentalStateValue, RentalSummary } from '@/api/contracts/rentals'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const props = defineProps<{ title: string; hint: string; emptyText: string; state: RentalStateValue; dateKey: 'starts_at' | 'ends_at' }>()
defineEmits<{ pick: [name: string] }>()

const { t, locale } = useI18n()
const search = ref('')
const rows = ref<RentalSummary[]>([])
const loading = ref(false)
const errorMessage = ref('')

const columns = computed<DataTableColumn<RentalSummary>[]>(() => [
  { key: props.dateKey, label: props.dateKey === 'starts_at' ? t('rentals.col_start') : t('rentals.col_end'), width: '180px', format: row => formatDateTime(row[props.dateKey], locale.value as LocaleType) },
  { key: 'name', label: t('rentals.col_id'), width: '170px' },
  { key: 'customer_name', label: t('rentals.col_customer'), width: '260px' },
  { key: 'project_name', label: t('rentals.col_project'), width: '260px' }
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().listRentalSummaries({ page: 1, page_size: 100, state: props.state, search: search.value || undefined })
    rows.value = [...result.items].sort((a, b) => a[props.dateKey].localeCompare(b[props.dateKey]))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})
onMounted(load)
</script>
