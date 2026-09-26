<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.rental_policies')">
      <template #title-suffix>
        <Tooltip v-if="data?.provenance === 'mock'" :text="t('admin.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button v-if="data?.can_edit_pricing" size="sm" variant="solid" @click="openRule()">
          <template #prefix><Plus class="size-4" :stroke-width="1.5" /></template>
          {{ t('admin.policies.add_rule') }}
        </Button>
      </template>
    </PageHeader>

    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>
    <p v-if="loading && !data" class="px-6 py-10 text-center text-p-base text-ink-gray-5" role="status">{{ t('table.loading') }}</p>

    <template v-if="data">
      <!-- Billable-days curve -->
      <section class="border-b border-outline-gray-1 px-6 py-5" :aria-labelledby="`${uid}-curve`">
        <h2 :id="`${uid}-curve`" class="text-base font-semibold text-ink-gray-9">{{ t('admin.policies.curve_title') }}</h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">{{ t('admin.policies.curve_hint') }}</p>
        <div class="mt-3 h-[240px]">
          <ECharts :options="curveOptions" class="h-full w-full" />
        </div>
      </section>

      <section class="py-5" :aria-labelledby="`${uid}-rules`">
        <h2 :id="`${uid}-rules`" class="px-6 pb-3 text-base font-semibold text-ink-gray-9">{{ t('admin.policies.rules_title') }}</h2>
        <DataTable
          :label="t('admin.policies.rules_title')"
          :columns="ruleColumns"
          :rows="data.rules"
          row-key="name"
          :filter-row="false"
          :empty-text="t('admin.policies.no_rules')"
          :clickable="data.can_edit_pricing"
          @row-click="row => openRule(row as PricingRule)"
        >
          <template #cell-is_active="{ row }">
            <Badge :theme="row.is_active ? 'green' : 'gray'" variant="subtle">{{ row.is_active ? t('admin.active') : t('admin.inactive') }}</Badge>
          </template>
        </DataTable>
      </section>

      <!-- Billing settings -->
      <section class="border-t border-outline-gray-1 px-6 py-5" :aria-labelledby="`${uid}-billing`">
        <div class="flex items-center gap-2">
          <h2 :id="`${uid}-billing`" class="text-base font-semibold text-ink-gray-9">{{ t('admin.policies.billing_title') }}</h2>
          <Badge v-if="!data.settings.configured" theme="gray" variant="subtle">{{ t('admin.policies.defaults') }}</Badge>
        </div>
        <p class="mt-1 text-p-sm text-ink-gray-5">{{ t('admin.policies.billing_hint') }}</p>
        <div class="mt-4 grid max-w-4xl grid-cols-1 gap-x-4 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
          <FormControl v-model="settings.advance_percentage" type="number" size="sm" variant="subtle" :label="t('admin.policies.advance_percentage')" :disabled="!data.can_edit_settings" min="0" max="100" />
          <FormControl v-model="settings.taxes_and_charges" type="select" size="sm" variant="subtle" :label="t('admin.policies.tax_template')" :options="taxOptions" :disabled="!data.can_edit_settings" />
          <label class="flex items-end gap-2 pb-1 text-base text-ink-gray-7">
            <Checkbox v-model="settings.include_equipment_guarantee" :disabled="!data.can_edit_settings" />
            {{ t('admin.policies.include_guarantee') }}
          </label>
          <FormControl v-model="settings.damage_item" type="text" size="sm" variant="subtle" :label="t('admin.policies.damage_item')" :placeholder="t('admin.policies.item_code')" :disabled="!data.can_edit_settings" />
          <FormControl v-model="settings.loss_item" type="text" size="sm" variant="subtle" :label="t('admin.policies.loss_item')" :placeholder="t('admin.policies.item_code')" :disabled="!data.can_edit_settings" />
        </div>
        <p v-if="settingsError" class="mt-3 text-p-sm text-ink-red-4" role="alert">{{ settingsError }}</p>
        <div v-if="data.can_edit_settings" class="mt-4 flex items-center gap-3">
          <Button size="sm" variant="solid" :loading="savingSettings" :disabled="!settingsDirty" @click="saveSettings">{{ t('admin.save') }}</Button>
          <span class="text-p-sm text-ink-gray-5">{{ t('admin.audited_hint') }}</span>
        </div>
      </section>
    </template>

    <Dialog v-model="ruleOpen" :options="{ title: ruleForm.existing ? t('admin.policies.edit_rule', { days: ruleForm.calendar_days }) : t('admin.policies.add_rule'), size: 'md' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl v-model="ruleForm.calendar_days" type="number" size="sm" variant="subtle" :label="t('admin.policies.calendar_days')" :disabled="ruleForm.existing" min="1" max="365" />
          <FormControl v-model="ruleForm.billable_days" type="number" size="sm" variant="subtle" :label="t('admin.policies.billable_days')" min="0.5" step="0.5" />
          <FormControl v-model="ruleForm.description" type="text" size="sm" variant="subtle" :label="t('admin.policies.description')" />
          <label class="flex items-center gap-2 text-base text-ink-gray-7"><Checkbox v-model="ruleForm.is_active" />{{ t('admin.active') }}</label>
          <p class="text-p-sm text-ink-gray-5">{{ t('admin.policies.rule_effect', { calendar: ruleForm.calendar_days || '…', billable: ruleForm.billable_days || '…', standard: standardFor(Number(ruleForm.calendar_days)) }) }}</p>
          <p v-if="ruleError" class="text-p-sm text-ink-red-4" role="alert">{{ ruleError }}</p>
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="subtle" :disabled="savingRule" @click="close">{{ t('common.cancel') }}</Button>
          <Button variant="solid" :loading="savingRule" :disabled="!ruleValid" @click="saveRule">{{ t('admin.save') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Checkbox, Dialog, ECharts, FormControl, Tooltip, toast } from 'frappe-ui'
import type { EChartsOption } from 'echarts'
import { Plus } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { CompanySettingsInput, Policies, PricingRule } from '@/api/contracts/administration'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const { t, locale } = useI18n()
const uid = useId()

const data = ref<Policies | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const settings = reactive({ advance_percentage: 30 as number | string, include_equipment_guarantee: true, taxes_and_charges: '', damage_item: '', loss_item: '' })
const savingSettings = ref(false)
const settingsError = ref('')
const ruleOpen = ref(false)
const savingRule = ref(false)
const ruleError = ref('')
const ruleForm = reactive({ existing: false, calendar_days: '' as number | string, billable_days: '' as number | string, description: '', is_active: true })

const ruleColumns = computed<DataTableColumn<PricingRule>[]>(() => [
  { key: 'calendar_days', label: t('admin.policies.calendar_days'), width: '160px', align: 'right' },
  { key: 'billable_days', label: t('admin.policies.billable_days'), width: '160px', align: 'right' },
  { key: 'standard', label: t('admin.policies.standard'), width: '160px', align: 'right', sortable: false, format: row => String(standardFor(row.calendar_days)) },
  { key: 'description', label: t('admin.policies.description'), width: '320px' },
  { key: 'is_active', label: t('admin.status'), width: '120px' },
  { key: 'modified', label: t('admin.modified'), width: '240px', format: row => `${formatDateTime(row.modified, locale.value as LocaleType)} · ${row.modified_by}` }
])

const taxOptions = computed(() => [{ label: '—', value: '' }, ...(data.value?.tax_templates ?? []).map(value => ({ label: value, value }))])

// Standard curve (services/pricing.py) — shown next to each override for comparison.
function standardFor(days: number): number | string {
  if (!days || days < 1) return '—'
  if (days <= 4) return [1, 1.5, 2, 2.5][days - 1]!
  if (days <= 7) return 3
  if (days <= 14) return 6
  if (days <= 30) return 10
  return Math.round(days * 0.4 * 100) / 100
}

const curveOptions = computed<EChartsOption>(() => {
  const curve = data.value?.curve ?? []
  return {
    grid: { top: 16, left: 40, right: 16, bottom: 28 },
    tooltip: { trigger: 'axis', formatter: (params: unknown) => {
      const point = (params as Array<{ dataIndex: number }>)[0]
      const entry = point ? curve[point.dataIndex] : undefined
      return entry ? t('admin.policies.curve_tooltip', { calendar: entry.calendar_days, billable: entry.billable_days, source: t(`admin.policies.source_${entry.source}`) }) : ''
    } },
    xAxis: { type: 'category', data: curve.map(p => String(p.calendar_days)), axisLabel: { color: '#7C7C7C' }, axisLine: { lineStyle: { color: '#E2E2E2' } } },
    yAxis: { type: 'value', axisLabel: { color: '#7C7C7C' }, splitLine: { lineStyle: { color: '#EDEDED' } } },
    series: [{
      type: 'line',
      step: 'end',
      data: curve.map(p => ({ value: p.billable_days, itemStyle: { color: p.source === 'rule' ? '#E789AD' : '#4B88D2' } })),
      lineStyle: { color: '#4B88D2', width: 2 },
      symbolSize: 6
    }]
  }
})

const settingsDirty = computed(() => {
  const s = data.value?.settings
  if (!s) return false
  return Number(settings.advance_percentage) !== s.advance_percentage || settings.include_equipment_guarantee !== s.include_equipment_guarantee ||
    settings.taxes_and_charges !== (s.taxes_and_charges ?? '') || settings.damage_item !== (s.damage_item ?? '') || settings.loss_item !== (s.loss_item ?? '')
})

const ruleValid = computed(() => {
  const calendar = Number(ruleForm.calendar_days)
  const billable = Number(ruleForm.billable_days)
  return Number.isInteger(calendar) && calendar >= 1 && calendar <= 365 && billable > 0 && billable <= calendar
})

function apply(result: Policies) {
  data.value = result
  Object.assign(settings, {
    advance_percentage: result.settings.advance_percentage,
    include_equipment_guarantee: result.settings.include_equipment_guarantee,
    taxes_and_charges: result.settings.taxes_and_charges ?? '',
    damage_item: result.settings.damage_item ?? '',
    loss_item: result.settings.loss_item ?? ''
  })
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    apply(await getCortexApiClient().getPolicies())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function openRule(rule?: PricingRule) {
  ruleError.value = ''
  Object.assign(ruleForm, rule
    ? { existing: true, calendar_days: rule.calendar_days, billable_days: rule.billable_days, description: rule.description, is_active: rule.is_active }
    : { existing: false, calendar_days: '', billable_days: '', description: '', is_active: true })
  ruleOpen.value = true
}

async function saveRule() {
  savingRule.value = true
  ruleError.value = ''
  try {
    apply(await getCortexApiClient().savePricingRule({ calendar_days: Number(ruleForm.calendar_days), billable_days: Number(ruleForm.billable_days), description: ruleForm.description, is_active: ruleForm.is_active }))
    ruleOpen.value = false
    toast.create({ message: t('admin.saved'), type: 'success' })
  } catch (error) {
    ruleError.value = error instanceof Error ? error.message : String(error)
  } finally {
    savingRule.value = false
  }
}

async function saveSettings() {
  savingSettings.value = true
  settingsError.value = ''
  const values: CompanySettingsInput = {
    advance_percentage: Number(settings.advance_percentage),
    include_equipment_guarantee: settings.include_equipment_guarantee,
    taxes_and_charges: settings.taxes_and_charges || null,
    damage_item: settings.damage_item.trim() || null,
    loss_item: settings.loss_item.trim() || null
  }
  try {
    apply(await getCortexApiClient().saveCompanySettings(values))
    toast.create({ message: t('admin.saved'), type: 'success' })
  } catch (error) {
    settingsError.value = error instanceof Error ? error.message : String(error)
  } finally {
    savingSettings.value = false
  }
}

onMounted(load)
</script>
