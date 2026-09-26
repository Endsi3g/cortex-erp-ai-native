<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.ai_audit')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock'" :text="t('ai.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" :disabled="!rows.length" @click="exportCsv">
          <template #prefix><Download class="size-4" :stroke-width="1.5" /></template>
          {{ t('ai.export_csv') }}
        </Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('routes.ai_audit')">
      <FormControl v-model="agent" type="select" size="sm" variant="subtle" :aria-label="t('ai.agent')" :options="agentOptions" />
      <FormControl v-model="status" type="select" size="sm" variant="subtle" :aria-label="t('ai.status')" :options="statusOptions" />
      <FormControl v-model="fromDate" type="date" size="sm" variant="subtle" :aria-label="t('ai.from_date')" />
      <FormControl v-model="toDate" type="date" size="sm" variant="subtle" :aria-label="t('ai.to_date')" />
    </PageFilters>
    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div class="mt-6">
      <DataTable
        :label="t('routes.ai_audit')"
        :columns="columns"
        :rows="rows"
        row-key="id"
        :loading="loading"
        :empty-text="t('ai.no_runs')"
        :total="total"
        :page="page"
        :page-size="pageSize"
        :page-sizes="[20, 100, 200]"
        clickable
        @row-click="row => (selected = row as AgentRun)"
        @update:page="value => (page = value)"
        @update:page-size="value => { pageSize = value; page = 1 }"
      >
        <template #cell-status="{ row }">
          <Badge :theme="row.status === 'Completed' ? 'green' : row.status === 'Failed' ? 'red' : 'blue'" variant="subtle">{{ t(`ai.run_${row.status}`) }}</Badge>
        </template>
      </DataTable>
      <p class="px-6 py-3 text-p-sm text-ink-gray-5">{{ t('ai.audit_hint') }}</p>
    </div>

    <Dialog :model-value="Boolean(selected)" :options="{ title: selected ? `${selected.agent} · ${selected.id}` : '', size: '3xl' }" @update:model-value="(value: boolean) => { if (!value) selected = null }">
      <template #body-content>
        <dl v-if="selected" class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-1.5 text-base">
          <dt class="text-ink-gray-5">{{ t('ai.request_id') }}</dt><dd class="font-mono text-ink-gray-8">{{ selected.request_id }}</dd>
          <dt class="text-ink-gray-5">{{ t('ai.actor') }}</dt><dd class="text-ink-gray-8">{{ selected.actor }}</dd>
          <dt class="text-ink-gray-5">{{ t('ai.model') }}</dt><dd class="text-ink-gray-8">{{ selected.model ?? '—' }}</dd>
          <dt class="text-ink-gray-5">{{ t('ai.started') }}</dt><dd class="text-ink-gray-8">{{ fmt(selected.started_at) }}</dd>
        </dl>
        <table v-if="selected" class="mt-4 w-full border-collapse border-t border-outline-gray-1 text-base">
          <thead>
            <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
              <th class="border-r border-outline-gray-1 px-2 text-left font-normal">{{ t('ai.tool') }}</th>
              <th class="border-r border-outline-gray-1 px-2 text-left font-normal">{{ t('ai.scope') }}</th>
              <th class="border-r border-outline-gray-1 px-2 text-left font-normal">{{ t('ai.status') }}</th>
              <th class="border-r border-outline-gray-1 px-2 text-right font-normal">{{ t('ai.duration') }}</th>
              <th class="px-2 text-left font-normal">{{ t('ai.error') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(call, index) in selected.tool_calls" :key="index" class="h-[33px] border-b border-outline-gray-1">
              <td class="border-r border-outline-gray-1 px-2 font-mono text-ink-gray-8">{{ call.tool_name }}</td>
              <td class="border-r border-outline-gray-1 px-2 font-mono text-ink-gray-6">{{ call.scope ?? '—' }}</td>
              <td class="border-r border-outline-gray-1 px-2"><Badge :theme="call.status === 'Success' ? 'green' : call.status === 'Denied' ? 'orange' : 'red'" variant="subtle">{{ t(`ai.call_${call.status}`) }}</Badge></td>
              <td class="border-r border-outline-gray-1 px-2 text-right text-ink-gray-8">{{ call.duration_ms === null ? '—' : `${call.duration_ms} ms` }}</td>
              <td class="px-2 text-ink-red-4">{{ call.error ?? '' }}</td>
            </tr>
            <tr v-if="!selected.tool_calls.length" class="h-[33px]"><td colspan="5" class="px-2 text-ink-gray-5">{{ t('ai.no_tool_calls') }}</td></tr>
          </tbody>
        </table>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dialog, FormControl, Tooltip } from 'frappe-ui'
import { Download } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { AgentRun } from '@/api/contracts/ai'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { downloadCsv, toCsv } from '@/utils/csv'

const { t, locale } = useI18n()

const agent = ref('')
const status = ref('')
const fromDate = ref('')
const toDate = ref('')
const page = ref(1)
const pageSize = ref(100)
const rows = ref<AgentRun[]>([])
const agents = ref<string[]>([])
const total = ref(0)
const provenance = ref<string | undefined>()
const loading = ref(false)
const errorMessage = ref('')
const selected = ref<AgentRun | null>(null)

const fmt = (value: string) => formatDateTime(value, locale.value as LocaleType)
const agentOptions = computed(() => [{ label: t('ai.all_agents'), value: '' }, ...agents.value.map(value => ({ label: value, value }))])
const statusOptions = computed(() => [{ label: t('ai.all_states'), value: '' }, ...['Running', 'Completed', 'Failed'].map(value => ({ label: t(`ai.run_${value}`), value }))])

const columns = computed<DataTableColumn<AgentRun>[]>(() => [
  { key: 'started_at', label: t('ai.started'), width: '170px', format: row => fmt(row.started_at) },
  { key: 'agent', label: t('ai.agent'), width: '200px' },
  { key: 'actor', label: t('ai.actor'), width: '220px' },
  { key: 'model', label: t('ai.model'), width: '160px', format: row => row.model ?? '—' },
  { key: 'tool_call_count', label: t('ai.tool_calls'), width: '110px', align: 'right' },
  { key: 'denied', label: t('ai.denied_or_failed'), width: '130px', align: 'right', sortable: false, format: row => String(row.tool_calls.filter(call => call.status !== 'Success').length) },
  { key: 'status', label: t('ai.status'), width: '130px' }
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().listAgentActivity({
      agent: agent.value || undefined,
      status: status.value || undefined,
      from_date: fromDate.value || undefined,
      to_date: toDate.value || undefined,
      page: page.value,
      page_size: pageSize.value
    })
    rows.value = result.items
    total.value = result.total_count
    agents.value = result.agents
    provenance.value = result.provenance
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  const header = ['run', 'started_at', 'agent', 'actor', 'model', 'status', 'tool', 'scope', 'tool_status', 'duration_ms', 'error']
  const lines: Array<Array<string | number | null>> = [header]
  for (const run of rows.value) {
    const calls = run.tool_calls.length ? run.tool_calls : [null]
    for (const call of calls) {
      lines.push([run.id, run.started_at, run.agent, run.actor, run.model, run.status, call?.tool_name ?? null, call?.scope ?? null, call?.status ?? null, call?.duration_ms ?? null, call?.error ?? null])
    }
  }
  downloadCsv(`agent-activity-${new Date().toISOString().slice(0, 10)}.csv`, toCsv(lines))
}

watch([agent, status, fromDate, toDate], () => {
  if (page.value !== 1) page.value = 1
  else void load()
})
watch([page, pageSize], () => void load())
onMounted(load)
</script>
