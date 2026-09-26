<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.ai_inbox')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock'" :text="t('ai.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" :loading="loading" @click="load">
          <template #prefix><RefreshCw class="size-4" :stroke-width="1.5" /></template>
          {{ t('ai.refresh') }}
        </Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('routes.ai_inbox')">
      <FormControl v-model="kind" type="select" size="sm" variant="subtle" :aria-label="t('ai.kind')" :options="kindOptions" />
      <FormControl v-model="state" type="select" size="sm" variant="subtle" :aria-label="t('ai.state')" :options="stateOptions" />
      <TextInput v-model="search" type="search" size="sm" variant="subtle" class="lg:col-span-2" :placeholder="t('ai.search')" :aria-label="t('ai.search')" />
      <label class="flex h-7 items-center gap-2 text-base text-ink-gray-7">
        <Checkbox v-model="includeClosed" />
        {{ t('ai.include_closed') }}
      </label>
    </PageFilters>
    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div class="mt-6">
      <DataTable
        :label="t('routes.ai_inbox')"
        :columns="columns"
        :rows="visibleRows"
        row-key="id"
        :loading="loading"
        :empty-text="t('ai.inbox_empty')"
        clickable
        @row-click="row => router.push({ name: 'ai-workspace', params: { itemId: String(row.id) } })"
      >
        <template #cell-title="{ row }">
          <span class="text-ink-gray-9">{{ row.title }}</span>
          <span class="ml-2 text-ink-gray-5">{{ t(`ai.kind_${row.kind}`) }}</span>
        </template>
        <template #cell-state="{ row }">
          <Badge :theme="INBOX_STATE_THEME[row.state as InboxState]" variant="subtle">{{ t(`ai.state_${row.state}`) }}</Badge>
        </template>
      </DataTable>
      <p class="px-6 py-3 text-p-sm text-ink-gray-5">{{ t('ai.score_legend') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Checkbox, FormControl, TextInput, Tooltip } from 'frappe-ui'
import { RefreshCw } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { InboxItem, InboxKind, InboxState } from '@/api/contracts/ai'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { INBOX_STATE_THEME, formatScore } from '../inboxStates'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const KINDS: InboxKind[] = ['approval', 'inbound', 'draft']
const STATES: InboxState[] = ['ready', 'needs_review', 'low_confidence', 'extraction_error', 'processing', 'validated', 'applied', 'rejected', 'expired']

const initialKind = typeof route.query.type === 'string' && KINDS.includes(route.query.type as InboxKind) ? route.query.type : ''
const kind = ref<string>(initialKind)
const state = ref('')
const search = ref('')
const includeClosed = ref(false)
const rows = ref<InboxItem[]>([])
const provenance = ref<string | undefined>()
const loading = ref(false)
const errorMessage = ref('')

const kindOptions = computed(() => [{ label: t('ai.all_kinds'), value: '' }, ...KINDS.map(value => ({ label: t(`ai.kind_${value}`), value }))])
const stateOptions = computed(() => [{ label: t('ai.all_states'), value: '' }, ...STATES.map(value => ({ label: t(`ai.state_${value}`), value }))])

const columns = computed<DataTableColumn<InboxItem>[]>(() => [
  { key: 'title', label: t('ai.item'), width: '380px' },
  { key: 'customer', label: t('ai.customer'), width: '200px' },
  { key: 'agent', label: t('ai.agent'), width: '170px', format: row => row.agent ?? '—' },
  { key: 'confidence', label: t('ai.model_score'), width: '120px', align: 'right', format: row => formatScore(row.confidence) },
  { key: 'state', label: t('ai.state'), width: '170px' },
  { key: 'created_at', label: t('ai.received'), width: '170px', format: row => formatDateTime(row.created_at, locale.value as LocaleType) }
])

const visibleRows = computed(() => {
  const needle = search.value.trim().toLowerCase()
  return rows.value.filter(row =>
    (!state.value || row.state === state.value) &&
    (!needle || [row.title, row.customer, row.reference, row.agent ?? '', row.requested_by ?? ''].some(value => value.toLowerCase().includes(needle)))
  )
})

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().listInbox((kind.value || undefined) as InboxKind | undefined, includeClosed.value)
    rows.value = result.items
    provenance.value = result.provenance
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

watch([kind, includeClosed], () => {
  void router.replace({ query: { type: kind.value || undefined } })
  void load()
})
onMounted(load)
</script>
