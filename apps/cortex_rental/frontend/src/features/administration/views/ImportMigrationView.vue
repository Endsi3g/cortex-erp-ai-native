<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="batch ? `${t('routes.import_migration')} · ${batch.name}` : t('routes.import_migration')">
      <template #title-suffix>
        <Badge v-if="batch" :theme="STATUS_THEME[batch.status]" variant="subtle" size="md">{{ t(`admin.import.status_${slug(batch.status)}`) }}</Badge>
        <Tooltip v-if="provenance === 'mock'" :text="t('admin.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button v-if="step > 0" size="sm" variant="subtle" @click="closeWizard">{{ t('admin.import.history') }}</Button>
        <Button v-else size="sm" variant="solid" @click="startNew">
          <template #prefix><Plus class="size-4" :stroke-width="1.5" /></template>
          {{ t('admin.import.new') }}
        </Button>
      </template>
    </PageHeader>

    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <!-- History -->
    <div v-if="step === 0" class="mt-2">
      <p class="px-6 py-3 text-p-sm text-ink-gray-5">{{ t('admin.import.intro') }}</p>
      <DataTable
        :label="t('admin.import.history')"
        :columns="historyColumns"
        :rows="history"
        row-key="name"
        :loading="loading"
        :empty-text="t('admin.import.no_batches')"
        clickable
        @row-click="row => openBatch(String(row.name))"
      >
        <template #cell-status="{ row }">
          <Badge :theme="STATUS_THEME[row.status as ImportStatus]" variant="subtle">{{ t(`admin.import.status_${slug(String(row.status))}`) }}</Badge>
        </template>
      </DataTable>
    </div>

    <!-- Wizard -->
    <template v-else>
      <ol class="flex flex-wrap gap-x-6 gap-y-2 border-b border-outline-gray-1 px-6 py-3 text-sm" :aria-label="t('admin.import.steps')">
        <li v-for="(label, index) in stepLabels" :key="label" class="flex items-center gap-2" :aria-current="step === index + 1 ? 'step' : undefined">
          <span class="flex size-5 items-center justify-center rounded-full text-xs" :class="step > index + 1 ? 'bg-surface-gray-7 text-ink-white' : step === index + 1 ? 'bg-surface-gray-7 text-ink-white ring-2 ring-outline-gray-3 ring-offset-1' : 'bg-surface-gray-2 text-ink-gray-5'">{{ index + 1 }}</span>
          <span :class="step === index + 1 ? 'font-medium text-ink-gray-9' : 'text-ink-gray-5'">{{ label }}</span>
        </li>
      </ol>

      <!-- 1. Type -->
      <section v-if="step === 1" class="max-w-3xl px-6 py-5">
        <h2 class="text-base font-semibold text-ink-gray-9">{{ t('admin.import.step_type') }}</h2>
        <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3" role="radiogroup" :aria-label="t('admin.import.step_type')">
          <button
            v-for="kind in IMPORT_TYPES"
            :key="kind"
            type="button"
            role="radio"
            :aria-checked="importType === kind"
            class="rounded border p-3 text-left hover:bg-surface-gray-1"
            :class="importType === kind ? 'border-outline-gray-5 bg-surface-gray-1' : 'border-outline-gray-2'"
            @click="importType = kind"
          >
            <span class="block text-base font-medium text-ink-gray-9">{{ t(`admin.import.type_${slug(kind)}`) }}</span>
            <span class="mt-1 block text-p-sm text-ink-gray-5">{{ t(`admin.import.type_${slug(kind)}_hint`) }}</span>
          </button>
        </div>
        <div v-if="specs" class="mt-4 text-p-sm text-ink-gray-6">
          {{ t('admin.import.expected_columns') }}
          <span v-for="(spec, index) in specs[importType]" :key="spec.field">{{ index ? ', ' : ' ' }}<span :class="spec.required ? 'font-medium text-ink-gray-9' : ''">{{ spec.label }}{{ spec.required ? ' *' : '' }}</span></span>
        </div>
        <Button class="mt-5" variant="solid" size="sm" :loading="busy" @click="createBatch">{{ t('admin.import.continue') }}</Button>
      </section>

      <!-- 2. File -->
      <section v-else-if="step === 2" class="max-w-3xl px-6 py-5">
        <h2 class="text-base font-semibold text-ink-gray-9">{{ t('admin.import.step_file') }}</h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">{{ t('admin.import.file_hint') }}</p>
        <label class="mt-4 flex cursor-pointer flex-col items-center justify-center gap-2 rounded border border-dashed border-outline-gray-3 px-6 py-10 text-center hover:bg-surface-gray-1">
          <Upload class="size-5 text-ink-gray-5" :stroke-width="1.5" aria-hidden="true" />
          <span class="text-base text-ink-gray-8">{{ busy ? t('admin.import.uploading') : t('admin.import.choose_file') }}</span>
          <input type="file" accept=".csv,text/csv" class="sr-only" :disabled="busy" @change="onFile" />
        </label>
      </section>

      <!-- 3. Mapping -->
      <section v-else-if="step === 3 && analysis" class="px-6 py-5">
        <h2 class="text-base font-semibold text-ink-gray-9">{{ t('admin.import.step_mapping') }}</h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">{{ t('admin.import.mapping_hint', { file: analysis.file_name, rows: analysis.total_rows }) }}</p>
        <div class="mt-4 grid max-w-4xl grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          <FormControl
            v-for="spec in batchSpecs"
            :key="spec.field"
            v-model="mapping[spec.field]"
            type="select"
            size="sm"
            variant="subtle"
            :label="`${spec.label}${spec.required ? ' *' : ''}`"
            :options="headerOptions"
          />
        </div>
        <h3 class="mb-2 mt-6 text-sm font-medium text-ink-gray-7">{{ t('admin.import.preview') }}</h3>
        <div class="overflow-x-auto">
          <table class="min-w-max border-collapse border-t border-outline-gray-1 text-base">
            <thead>
              <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
                <th class="w-[37px] border-r border-outline-gray-1 font-normal">#</th>
                <th v-for="header in analysis.headers" :key="header" class="border-r border-outline-gray-1 px-2 text-left font-normal">
                  {{ header }}<span v-if="mappedTo(header)" class="ml-1 text-ink-gray-4">→ {{ mappedTo(header) }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in analysis.preview" :key="index" class="h-[33px] border-b border-outline-gray-1">
                <td class="border-r border-outline-gray-1 text-center text-ink-gray-5">{{ index + 2 }}</td>
                <td v-for="(cell, cellIndex) in row" :key="cellIndex" class="max-w-[240px] truncate border-r border-outline-gray-1 px-2 text-ink-gray-8">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="mt-5 flex gap-2">
          <Button variant="subtle" size="sm" :disabled="busy" @click="step = 2">{{ t('admin.import.change_file') }}</Button>
          <Button variant="solid" size="sm" :loading="busy" :disabled="!mappingComplete" @click="runValidation">{{ t('admin.import.validate') }}</Button>
        </div>
      </section>

      <!-- 4. Validation -->
      <section v-else-if="step === 4 && validation" class="px-6 py-5">
        <h2 class="text-base font-semibold text-ink-gray-9">{{ t('admin.import.step_validation') }}</h2>
        <dl class="mt-4 flex flex-wrap gap-8">
          <div><dt class="text-p-sm text-ink-gray-5">{{ t('admin.import.rows') }}</dt><dd class="text-2xl font-semibold text-ink-gray-9">{{ validation.total_rows }}</dd></div>
          <div><dt class="text-p-sm text-ink-gray-5">{{ t('admin.import.valid_rows') }}</dt><dd class="text-2xl font-semibold text-ink-green-3">{{ validation.valid_rows }}</dd></div>
          <div><dt class="text-p-sm text-ink-gray-5">{{ t('admin.import.error_rows') }}</dt><dd class="text-2xl font-semibold" :class="validation.error_rows ? 'text-ink-red-4' : 'text-ink-gray-9'">{{ validation.error_rows }}</dd></div>
        </dl>
        <template v-if="validation.errors.length">
          <h3 class="mb-2 mt-6 text-sm font-medium text-ink-gray-7">{{ t('admin.import.errors_title') }}</h3>
          <ErrorTable :errors="validation.errors" />
        </template>
        <p class="mt-5 text-p-sm text-ink-gray-6">{{ validation.valid_rows ? t('admin.import.import_effect', { count: validation.valid_rows, type: t(`admin.import.type_${slug(batch?.import_type ?? '')}`) }) : t('admin.import.nothing_to_import') }}</p>
        <div class="mt-3 flex gap-2">
          <Button variant="subtle" size="sm" :disabled="busy" @click="backToMapping">{{ t('admin.import.fix_mapping') }}</Button>
          <Button variant="solid" size="sm" :loading="busy" :disabled="!validation.valid_rows" @click="runImport">{{ t('admin.import.import_rows', { count: validation.valid_rows }) }}</Button>
        </div>
      </section>

      <!-- 5. Importing -->
      <section v-else-if="step === 5" class="px-6 py-10 text-center" role="status">
        <p class="text-base text-ink-gray-8">{{ t('admin.import.importing') }}</p>
        <p class="mt-1 text-p-sm text-ink-gray-5">{{ t('admin.import.importing_hint') }}</p>
      </section>

      <!-- 6. Result -->
      <section v-else-if="step === 6 && batch" class="px-6 py-5">
        <h2 class="text-base font-semibold text-ink-gray-9">{{ t('admin.import.step_result') }}</h2>
        <dl class="mt-4 grid max-w-3xl grid-cols-[180px_1fr] gap-x-4 gap-y-1.5 text-base">
          <dt class="text-ink-gray-5">{{ t('admin.import.type') }}</dt><dd class="text-ink-gray-8">{{ t(`admin.import.type_${slug(batch.import_type)}`) }}</dd>
          <dt class="text-ink-gray-5">{{ t('admin.import.file') }}</dt><dd class="text-ink-gray-8">{{ batch.source_file_name || '—' }}</dd>
          <dt class="text-ink-gray-5">{{ t('admin.import.imported_rows') }}</dt><dd class="text-ink-gray-8">{{ batch.imported_rows }} / {{ batch.total_rows }}</dd>
          <dt class="text-ink-gray-5">{{ t('admin.import.imported_by') }}</dt><dd class="text-ink-gray-8">{{ batch.imported_by || '—' }}<template v-if="batch.imported_at"> · {{ fmt(batch.imported_at) }}</template></dd>
          <template v-if="batch.rolled_back_at">
            <dt class="text-ink-gray-5">{{ t('admin.import.rolled_back_by') }}</dt><dd class="text-ink-gray-8">{{ batch.rolled_back_by }} · {{ fmt(batch.rolled_back_at) }}</dd>
          </template>
        </dl>
        <template v-if="batch.row_errors.length">
          <h3 class="mb-2 mt-6 text-sm font-medium text-ink-gray-7">{{ t('admin.import.errors_title') }}</h3>
          <ErrorTable :errors="batch.row_errors" />
        </template>
        <template v-if="kept.length">
          <h3 class="mb-2 mt-6 text-sm font-medium text-ink-red-4">{{ t('admin.import.kept_title') }}</h3>
          <ul class="list-disc space-y-0.5 pl-5 text-p-sm text-ink-gray-7">
            <li v-for="item in kept" :key="`${item.doctype}:${item.name}`">{{ item.doctype }} {{ item.name }} — {{ item.reason }}</li>
          </ul>
        </template>
        <h3 class="mb-2 mt-6 text-sm font-medium text-ink-gray-7">{{ t('admin.import.records_title', { count: batch.records.length }) }}</h3>
        <DataTable :label="t('admin.import.records_title', { count: batch.records.length })" :columns="recordColumns" :rows="batch.records" row-key="name" :filter-row="false" :empty-text="t('admin.import.no_records')">
          <template #cell-rolled_back="{ row }">
            <Badge :theme="row.rolled_back ? 'gray' : 'green'" variant="subtle">{{ row.rolled_back ? t('admin.import.record_removed') : t('admin.import.record_created') }}</Badge>
          </template>
        </DataTable>
        <div v-if="canRollback" class="mt-5">
          <Button variant="subtle" theme="red" size="sm" @click="rollbackOpen = true">{{ t('admin.import.rollback') }}</Button>
          <p class="mt-2 text-p-sm text-ink-gray-5">{{ t('admin.import.rollback_hint') }}</p>
        </div>
      </section>
    </template>

    <ReasonDialog
      v-model="rollbackOpen"
      :title="t('admin.import.rollback')"
      :label="t('admin.reason')"
      :description="t('admin.import.rollback_effect', { count: activeRecords })"
      :confirm-label="t('admin.import.rollback_confirm')"
      :cancel-label="t('common.cancel')"
      danger
      :loading="busy"
      :error="rollbackError"
      @confirm="runRollback"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, FormControl, Tooltip, toast } from 'frappe-ui'
import { Plus, Upload } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import ReasonDialog from '@/design-system/components/page/ReasonDialog.vue'
import { getCortexApiClient } from '@/api'
import type { ImportAnalysis, ImportBatch, ImportBatchRow, ImportFieldSpec, ImportRowError, ImportStatus, ImportType, ImportValidation } from '@/api/contracts/administration'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

type BadgeTheme = 'gray' | 'blue' | 'green' | 'orange' | 'red'
const IMPORT_TYPES: ImportType[] = ['Customers', 'Equipment', 'Serial Numbers']
const STATUS_THEME: Record<ImportStatus, BadgeTheme> = { Draft: 'gray', Validated: 'blue', Imported: 'green', 'Partially Imported': 'orange', 'Rolled Back': 'gray', Failed: 'red' }

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const api = getCortexApiClient()

const slug = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '_')
const fmt = (value: string) => formatDateTime(value, locale.value as LocaleType)

const step = ref(0)
const history = ref<ImportBatchRow[]>([])
const specs = ref<Record<ImportType, ImportFieldSpec[]> | null>(null)
const provenance = ref<string | undefined>()
const loading = ref(false)
const busy = ref(false)
const errorMessage = ref('')
const importType = ref<ImportType>('Customers')
const batch = ref<ImportBatch | null>(null)
const analysis = ref<ImportAnalysis | null>(null)
const mapping = reactive<Record<string, string>>({})
const validation = ref<ImportValidation | null>(null)
const kept = ref<Array<{ doctype: string; name: string; reason: string }>>([])
const rollbackOpen = ref(false)
const rollbackError = ref('')

const stepLabels = computed(() => [t('admin.import.step_type'), t('admin.import.step_file'), t('admin.import.step_mapping'), t('admin.import.step_validation'), t('admin.import.step_import'), t('admin.import.step_result')])
const batchSpecs = computed(() => (batch.value && specs.value ? specs.value[batch.value.import_type] : []))
const headerOptions = computed(() => [{ label: t('admin.import.ignore'), value: '' }, ...(analysis.value?.headers ?? []).map(value => ({ label: value, value }))])
const mappingComplete = computed(() => batchSpecs.value.every(spec => !spec.required || mapping[spec.field]))
const activeRecords = computed(() => batch.value?.records.filter(r => !r.rolled_back).length ?? 0)
const canRollback = computed(() => Boolean(batch.value && ['Imported', 'Partially Imported'].includes(batch.value.status) && activeRecords.value))

const historyColumns = computed<DataTableColumn<ImportBatchRow>[]>(() => [
  { key: 'name', label: t('admin.import.batch'), width: '150px' },
  { key: 'import_type', label: t('admin.import.type'), width: '170px', format: row => t(`admin.import.type_${slug(row.import_type)}`) },
  { key: 'source_file_name', label: t('admin.import.file'), width: '220px', format: row => row.source_file_name ?? '—' },
  { key: 'status', label: t('admin.status'), width: '160px' },
  { key: 'total_rows', label: t('admin.import.rows'), width: '90px', align: 'right' },
  { key: 'imported_rows', label: t('admin.import.imported_rows'), width: '120px', align: 'right' },
  { key: 'error_rows', label: t('admin.import.error_rows'), width: '110px', align: 'right' },
  { key: 'created_at', label: t('admin.import.created'), width: '220px', format: row => `${fmt(row.created_at)} · ${row.created_by}` }
])
const recordColumns = computed<DataTableColumn<ImportBatch['records'][number] & Record<string, unknown>>[]>(() => [
  { key: 'line', label: t('admin.import.line'), width: '90px', align: 'right' },
  { key: 'doctype', label: 'DocType', width: '240px' },
  { key: 'name', label: t('admin.import.document'), width: '260px' },
  { key: 'rolled_back', label: t('admin.status'), width: '140px' }
])

// Row-level errors: line number and every problem found on it.
const ErrorTable = defineComponent({
  props: { errors: { type: Array as () => ImportRowError[], required: true } },
  setup(props) {
    return () => h('div', { class: 'max-h-[360px] overflow-auto' }, [
      h('table', { class: 'w-full border-collapse border-t border-outline-gray-1 text-base' }, [
        h('thead', h('tr', { class: 'h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6' }, [
          h('th', { class: 'w-[90px] border-r border-outline-gray-1 px-2 text-right font-normal' }, t('admin.import.line')),
          h('th', { class: 'px-2 text-left font-normal' }, t('admin.import.problems'))
        ])),
        h('tbody', props.errors.map(error => h('tr', { key: error.line, class: 'h-[33px] border-b border-outline-gray-1' }, [
          h('td', { class: 'border-r border-outline-gray-1 px-2 text-right text-ink-gray-8' }, String(error.line)),
          h('td', { class: 'px-2 text-ink-red-4' }, error.errors.join(' · '))
        ])))
      ])
    ])
  }
})

function fail(error: unknown) {
  errorMessage.value = error instanceof Error ? error.message : String(error)
}

async function loadHistory() {
  loading.value = true
  try {
    const result = await api.listImportBatches()
    history.value = result.items
    specs.value = result.specs
    provenance.value = result.provenance
  } catch (error) {
    fail(error)
  } finally {
    loading.value = false
  }
}

function resetWizard() {
  batch.value = null
  analysis.value = null
  validation.value = null
  kept.value = []
  for (const key of Object.keys(mapping)) delete mapping[key]
  errorMessage.value = ''
}

function startNew() {
  resetWizard()
  importType.value = 'Customers'
  step.value = 1
}

function closeWizard() {
  resetWizard()
  step.value = 0
  void router.replace({ query: {} })
  void loadHistory()
}

async function createBatch() {
  busy.value = true
  errorMessage.value = ''
  try {
    batch.value = await api.createImportBatch(importType.value)
    void router.replace({ query: { batch: batch.value.name } })
    step.value = 2
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function analyze() {
  if (!batch.value) return
  analysis.value = await api.analyzeImport(batch.value.name)
  for (const spec of batchSpecs.value) mapping[spec.field] = analysis.value.mapping[spec.field] ?? ''
  step.value = 3
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !batch.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    await api.uploadImportFile(batch.value.name, file)
    await analyze()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

function mappedTo(header: string) {
  const field = Object.keys(mapping).find(key => mapping[key] === header)
  return field ? batchSpecs.value.find(spec => spec.field === field)?.label : ''
}

async function runValidation() {
  if (!batch.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    const cleaned = Object.fromEntries(batchSpecs.value.map(spec => [spec.field, mapping[spec.field] || null]))
    validation.value = await api.validateImport(batch.value.name, cleaned)
    batch.value = await api.getImportBatch(batch.value.name)
    step.value = 4
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function backToMapping() {
  busy.value = true
  try {
    if (!analysis.value) await analyze()
    step.value = 3
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function runImport() {
  if (!batch.value) return
  busy.value = true
  errorMessage.value = ''
  step.value = 5
  try {
    batch.value = await api.runImport(batch.value.name)
    step.value = 6
    toast.create({ message: t('admin.import.done', { count: batch.value.imported_rows }), type: 'success' })
  } catch (error) {
    step.value = 4
    fail(error)
  } finally {
    busy.value = false
  }
}

async function runRollback(reason: string) {
  if (!batch.value) return
  busy.value = true
  rollbackError.value = ''
  try {
    const result = await api.rollbackImport(batch.value.name, reason)
    kept.value = result.kept
    batch.value = await api.getImportBatch(batch.value.name)
    rollbackOpen.value = false
    toast.create({ message: t('admin.import.rolled_back', { count: result.deleted }), type: 'success' })
  } catch (error) {
    rollbackError.value = error instanceof Error ? error.message : String(error)
  } finally {
    busy.value = false
  }
}

async function openBatch(name: string) {
  resetWizard()
  busy.value = true
  try {
    batch.value = await api.getImportBatch(name)
    void router.replace({ query: { batch: name } })
    if (batch.value.status === 'Draft') {
      step.value = 2
    } else if (batch.value.status === 'Validated') {
      validation.value = { total_rows: batch.value.total_rows, valid_rows: batch.value.valid_rows, error_rows: batch.value.error_rows, errors: batch.value.row_errors, sample: [] }
      step.value = 4
    } else {
      step.value = 6
    }
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  await loadHistory()
  if (typeof route.query.batch === 'string') await openBatch(route.query.batch)
})
</script>
