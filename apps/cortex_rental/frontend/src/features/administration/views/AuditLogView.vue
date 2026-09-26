<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.audit_log')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock'" :text="t('admin.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" :loading="exporting" :disabled="!total" @click="exportCsv">
          <template #prefix><Download class="size-4" :stroke-width="1.5" /></template>
          {{ t('admin.audit.export', { count: Math.min(total, EXPORT_LIMIT) }) }}
        </Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('routes.audit_log')">
      <TextInput v-model="filters.action" type="search" size="sm" variant="subtle" :placeholder="t('admin.audit.action')" :aria-label="t('admin.audit.action')" />
      <FormControl v-model="filters.entity_type" type="select" size="sm" variant="subtle" :aria-label="t('admin.audit.entity_type')" :options="entityOptions" />
      <TextInput v-model="filters.entity_id" type="search" size="sm" variant="subtle" :placeholder="t('admin.audit.entity_id')" :aria-label="t('admin.audit.entity_id')" />
      <TextInput v-model="filters.actor" type="search" size="sm" variant="subtle" :placeholder="t('admin.audit.actor')" :aria-label="t('admin.audit.actor')" />
      <FormControl v-model="filters.actor_type" type="select" size="sm" variant="subtle" :aria-label="t('admin.audit.actor_type')" :options="actorTypeOptions" />
      <div class="flex gap-2 sm:col-span-2">
        <FormControl v-model="filters.from_date" type="date" size="sm" variant="subtle" class="flex-1" :aria-label="t('admin.audit.from')" />
        <FormControl v-model="filters.to_date" type="date" size="sm" variant="subtle" class="flex-1" :aria-label="t('admin.audit.to')" />
      </div>
    </PageFilters>
    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div class="mt-6">
      <DataTable
        :label="t('routes.audit_log')"
        :columns="columns"
        :rows="rows"
        row-key="name"
        :loading="loading"
        :empty-text="t('admin.audit.empty')"
        :total="total"
        :page="page"
        :page-size="pageSize"
        :page-sizes="[20, 100, 500]"
        clickable
        @row-click="row => openEvent(String(row.name))"
        @update:page="value => (page = value)"
        @update:page-size="value => { pageSize = value; page = 1 }"
      >
        <template #cell-actor_type="{ row }">
          <Badge :theme="row.actor_type === 'Agent' ? 'blue' : row.actor_type === 'System' ? 'gray' : 'green'" variant="subtle">{{ t(`admin.audit.actor_${row.actor_type}`) }}</Badge>
        </template>
        <template #cell-action="{ row }"><span class="font-mono text-sm">{{ row.action }}</span></template>
      </DataTable>
      <p class="px-6 py-3 text-p-sm text-ink-gray-5">{{ t('admin.audit.hint') }}</p>
    </div>

    <Dialog :model-value="Boolean(detail) || detailLoading" :options="{ title: detail?.action ?? '', size: '4xl' }" @update:model-value="(value: boolean) => { if (!value) detail = null }">
      <template #body-content>
        <p v-if="detailLoading" class="text-p-base text-ink-gray-5" role="status">{{ t('table.loading') }}</p>
        <template v-else-if="detail">
          <dl class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-1.5 text-base">
            <dt class="text-ink-gray-5">{{ t('admin.audit.when') }}</dt><dd class="text-ink-gray-8">{{ fmt(detail.timestamp) }}</dd>
            <dt class="text-ink-gray-5">{{ t('admin.audit.actor') }}</dt><dd class="text-ink-gray-8">{{ detail.actor_id }} · {{ t(`admin.audit.actor_${detail.actor_type}`) }}</dd>
            <dt class="text-ink-gray-5">{{ t('admin.audit.entity') }}</dt><dd class="text-ink-gray-8">{{ detail.entity_type }} {{ detail.entity_id }}</dd>
            <dt class="text-ink-gray-5">{{ t('admin.audit.request') }}</dt><dd class="font-mono text-ink-gray-8">{{ detail.request_id || '—' }}</dd>
          </dl>
          <div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
            <div v-for="block in detailBlocks" :key="block.key">
              <h3 class="mb-1 text-sm font-medium text-ink-gray-7">{{ block.label }}</h3>
              <pre class="max-h-[300px] overflow-auto whitespace-pre-wrap rounded border border-outline-gray-1 bg-surface-gray-1 p-2 font-mono text-xs text-ink-gray-8">{{ block.value }}</pre>
            </div>
          </div>
        </template>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dialog, FormControl, TextInput, Tooltip, toast } from 'frappe-ui'
import { Download } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { AuditEventDetail, AuditQuery, AuditRow } from '@/api/contracts/administration'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { downloadCsv, toCsv } from '@/utils/csv'

const EXPORT_LIMIT = 5000
const { t, locale } = useI18n()

const filters = reactive({ action: '', entity_type: '', entity_id: '', actor: '', actor_type: '', from_date: '', to_date: '' })
const page = ref(1)
const pageSize = ref(100)
const rows = ref<AuditRow[]>([])
const total = ref(0)
const entityTypes = ref<string[]>([])
const provenance = ref<string | undefined>()
const loading = ref(false)
const exporting = ref(false)
const errorMessage = ref('')
const detail = ref<AuditEventDetail | null>(null)
const detailLoading = ref(false)

const fmt = (value: string) => formatDateTime(value, locale.value as LocaleType)
const entityOptions = computed(() => [{ label: t('admin.audit.all_entities'), value: '' }, ...entityTypes.value.map(value => ({ label: value, value }))])
const actorTypeOptions = computed(() => [{ label: t('admin.audit.all_actors'), value: '' }, ...['Human', 'Agent', 'System'].map(value => ({ label: t(`admin.audit.actor_${value}`), value }))])

const columns = computed<DataTableColumn<AuditRow>[]>(() => [
  { key: 'timestamp', label: t('admin.audit.when'), width: '170px', format: row => fmt(row.timestamp) },
  { key: 'actor_type', label: t('admin.audit.actor_type'), width: '110px' },
  { key: 'actor_id', label: t('admin.audit.actor'), width: '230px' },
  { key: 'action', label: t('admin.audit.action'), width: '300px' },
  { key: 'entity_type', label: t('admin.audit.entity_type'), width: '220px' },
  { key: 'entity_id', label: t('admin.audit.entity_id'), width: '200px' }
])

const detailBlocks = computed(() => {
  if (!detail.value) return []
  const show = (value: unknown) => (value === null || value === undefined ? '—' : typeof value === 'string' ? value : JSON.stringify(value, null, 2))
  return [
    { key: 'before', label: t('admin.audit.before'), value: show(detail.value.before_state) },
    { key: 'after', label: t('admin.audit.after'), value: show(detail.value.after_state) },
    { key: 'evidence', label: t('admin.audit.evidence'), value: show(detail.value.evidence) },
    { key: 'policy', label: t('admin.audit.policy'), value: show(detail.value.policy_decision) }
  ]
})

function query(pageNumber: number, size: number): AuditQuery {
  const cleaned = Object.fromEntries(Object.entries(filters).map(([key, value]) => [key, value.trim() || undefined]))
  return { ...cleaned, page: pageNumber, page_size: size }
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().listAuditEvents(query(page.value, pageSize.value))
    rows.value = result.items
    total.value = result.total_count
    entityTypes.value = result.entity_types
    provenance.value = result.provenance
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function openEvent(name: string) {
  detailLoading.value = true
  try {
    detail.value = await getCortexApiClient().getAuditEvent(name)
  } catch (error) {
    toast.create({ message: error instanceof Error ? error.message : String(error), type: 'error' })
  } finally {
    detailLoading.value = false
  }
}

async function exportCsv() {
  exporting.value = true
  try {
    const result = await getCortexApiClient().listAuditEvents(query(1, EXPORT_LIMIT))
    const lines: Array<Array<string | null>> = [['timestamp', 'actor_type', 'actor_id', 'action', 'entity_type', 'entity_id', 'request_id', 'event']]
    for (const row of result.items) lines.push([row.timestamp, row.actor_type, row.actor_id, row.action, row.entity_type, row.entity_id, row.request_id, row.name])
    downloadCsv(`audit-${new Date().toISOString().slice(0, 10)}.csv`, toCsv(lines))
  } catch (error) {
    toast.create({ message: error instanceof Error ? error.message : String(error), type: 'error' })
  } finally {
    exporting.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(filters, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    if (page.value !== 1) page.value = 1
    else void load()
  }, 250)
})
watch([page, pageSize], () => void load())
onMounted(load)
</script>
