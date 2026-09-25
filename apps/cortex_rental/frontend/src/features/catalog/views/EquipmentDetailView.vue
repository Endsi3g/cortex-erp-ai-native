<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="record?.item_name || String(route.params.item)">
      <template #title-suffix>
        <Badge v-if="record" theme="gray" variant="subtle" size="md">{{ record.category }}</Badge>
        <Tooltip v-if="record?.provenance === 'mock'" :text="t('catalog.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template v-if="record" #actions>
        <Button v-if="record.can_edit" size="sm" variant="subtle" @click="openEdit">{{ t('catalog.edit_profile') }}</Button>
        <Button size="sm" variant="solid" :route="{ name: 'rental-composer', query: { items: record.item_code } }">{{ t('catalog.add_to_rental') }}</Button>
      </template>
    </PageHeader>

    <p v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>
    <div v-else-if="!record" class="mx-6 mt-10 flex items-center gap-2 text-base text-ink-gray-5" role="status"><LoadingIndicator class="size-4" /> {{ t('table.loading') }}</div>

    <template v-else>
      <dl class="grid grid-cols-2 gap-x-8 gap-y-4 border-b border-outline-gray-1 px-6 py-5 md:grid-cols-3 xl:grid-cols-6">
        <div><dt class="text-sm text-ink-gray-5">{{ t('catalog.code') }}</dt><dd class="mt-1 text-base">{{ record.item_code }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('rental_detail.daily_rate') }}</dt><dd class="mt-1 text-base font-semibold tabular-nums">{{ money(record.daily_rate) }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('catalog.replacement_value') }}</dt><dd class="mt-1 text-base tabular-nums">{{ money(record.replacement_value) }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('catalog.guarantee') }}</dt><dd class="mt-1 text-base tabular-nums">{{ money(record.deposit_required) }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('catalog.prep_hours') }}</dt><dd class="mt-1 text-base">{{ t('catalog.hours', { hours: record.prep_hours }) }}</dd></div>
        <div>
          <dt class="text-sm text-ink-gray-5">{{ t('catalog.fleet') }}</dt>
          <dd class="mt-1 text-base">{{ t('catalog.fleet_value', { total: record.fleet.total, active: record.fleet.active, out: record.fleet.out, unavailable: record.fleet.unavailable }) }}</dd>
        </div>
      </dl>
      <p v-if="record.description" class="border-b border-outline-gray-1 px-6 py-3 text-p-base text-ink-gray-7">{{ stripHtml(record.description) }}</p>

      <div class="px-6 pt-5">
        <TabButtons v-model="tab" :buttons="tabs" />
      </div>

      <section v-if="tab === 'units'" class="mt-4">
        <DataTable :label="t('catalog.units')" :columns="serialColumns" :rows="record.serials" row-key="serial_no" :empty-text="record.is_serialized ? t('catalog.no_serials') : t('catalog.bulk_item', { qty: record.total_quantity })" clickable @row-click="row => router.push({ name: 'serial-detail', params: { serial: String(row.serial_no) } })">
          <template #cell-status="{ row }"><SerialStatusBadge :status="row.status as SerialStatus" /></template>
          <template #cell-current_rental="{ row }">
            <RouterLink v-if="row.current_rental" :to="{ name: 'rental-detail', params: { name: String(row.current_rental) } }" class="underline decoration-outline-gray-3 underline-offset-2" @click.stop>{{ row.current_rental }}</RouterLink>
          </template>
        </DataTable>
      </section>

      <section v-else-if="tab === 'pricing'" class="mt-4">
        <DataTable :label="t('catalog.pricing')" :columns="curveColumns" :rows="curveRows" row-key="calendar_days" :filter-row="false" />
        <p class="px-6 py-3 text-p-sm text-ink-gray-5">{{ t('catalog.pricing_note') }}</p>
      </section>

      <section v-else-if="tab === 'accessories'" class="px-6 py-4">
        <ul v-if="record.required_accessories.length" class="list-inside list-disc space-y-1 text-base text-ink-gray-8">
          <li v-for="accessory in record.required_accessories" :key="accessory">{{ accessory }}</li>
        </ul>
        <p v-else class="text-p-base text-ink-gray-5">{{ t('catalog.no_accessories') }}</p>
      </section>

      <section v-else-if="tab === 'availability'" class="mt-4">
        <AvailabilityGrid :label="t('catalog.availability_14')" :empty-text="t('availability.empty')" :rows="matrixRows" :range-start="rangeStart" :range-end="rangeEnd" granularity="month" :selected="[]" @select-block="block => router.push({ name: 'rental-detail', params: { name: block.rental_id } })" />
      </section>
    </template>

    <Dialog v-model="editOpen" :options="{ title: t('catalog.edit_profile'), size: 'lg' }">
      <template #body-content>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FormControl v-model="edit.daily_rate" type="number" size="sm" variant="subtle" :label="t('rental_detail.daily_rate')" />
          <FormControl v-model="edit.replacement_value" type="number" size="sm" variant="subtle" :label="t('catalog.replacement_value')" />
          <FormControl v-model="edit.deposit_required" type="number" size="sm" variant="subtle" :label="t('catalog.guarantee')" />
          <FormControl v-model="edit.prep_hours" type="number" size="sm" variant="subtle" :label="t('catalog.prep_hours')" />
          <FormControl v-if="!record?.is_serialized" v-model="edit.total_quantity" type="number" size="sm" variant="subtle" :label="t('catalog.bulk_quantity')" />
          <FormControl v-model="edit.required_accessories" type="text" size="sm" variant="subtle" class="sm:col-span-2" :label="t('catalog.accessories_csv')" />
        </div>
        <p class="mt-3 text-p-sm text-ink-gray-5">{{ t('catalog.edit_audit_note') }}</p>
        <p v-if="editError" class="mt-2 text-p-sm text-ink-red-4" role="alert">{{ editError }}</p>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="subtle" :disabled="saving" @click="close">{{ t('common.cancel') }}</Button>
          <Button variant="solid" :loading="saving" @click="saveEdit">{{ t('composer.save_changes') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dialog, FormControl, LoadingIndicator, TabButtons, Tooltip, toast } from 'frappe-ui'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { EquipmentRecord, EquipmentSerial, SerialStatus } from '@/api/contracts/catalog'
import type { MatrixEquipmentRow } from '@/api/contracts/availability'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import AvailabilityGrid from '@/features/availability/components/AvailabilityGrid.vue'
import SerialStatusBadge from '../components/SerialStatusBadge.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const record = ref<EquipmentRecord | null>(null)
const errorMessage = ref('')
const tab = ref<'units' | 'pricing' | 'accessories' | 'availability'>('units')
const matrixRows = ref<MatrixEquipmentRow[]>([])
const editOpen = ref(false)
const saving = ref(false)
const editError = ref('')
const edit = reactive({ daily_rate: '', replacement_value: '', deposit_required: '', prep_hours: '', total_quantity: '', required_accessories: '' })

const money = (value: number) => formatMoney(value, record.value?.currency, locale.value as LocaleType)
const stripHtml = (value: string) => value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()

const tabs = computed(() => [
  { label: t('catalog.units'), value: 'units' },
  { label: t('catalog.pricing'), value: 'pricing' },
  { label: t('catalog.accessories'), value: 'accessories' },
  { label: t('catalog.availability_14'), value: 'availability' }
])

const serialColumns = computed<DataTableColumn<EquipmentSerial>[]>(() => [
  { key: 'serial_no', label: t('rental_detail.serial'), width: '220px' },
  { key: 'status', label: t('finance.invoices.state'), width: '160px' },
  { key: 'current_rental', label: t('catalog.current_rental'), width: '200px' },
  { key: 'warranty_expiry_date', label: t('catalog.warranty'), width: '160px' }
])

type CurveRow = EquipmentRecord['pricing_curve'][number] & Record<string, unknown>
const curveRows = computed(() => (record.value?.pricing_curve ?? []) as CurveRow[])
const curveColumns = computed<DataTableColumn<CurveRow>[]>(() => [
  { key: 'calendar_days', label: t('catalog.calendar_days'), width: '160px', align: 'right' },
  { key: 'billable_days', label: t('rentals.col_billable_days'), width: '160px', align: 'right' },
  { key: 'price', label: t('catalog.period_price'), width: '180px', align: 'right', format: row => money(row.price) }
])

const rangeStart = computed(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d })
const rangeEnd = computed(() => { const d = new Date(rangeStart.value); d.setDate(d.getDate() + 14); return d })
const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

async function load() {
  errorMessage.value = ''
  try {
    record.value = await getCortexApiClient().getEquipment({ item_code: String(route.params.item) })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

async function loadAvailability() {
  if (!record.value) return
  try {
    const result = await getCortexApiClient().getAvailabilityMatrix({ start_date: ymd(rangeStart.value), end_date: ymd(new Date(rangeEnd.value.getTime() - 1)), view_mode: 'week', search: record.value.item_code })
    matrixRows.value = result.rows.filter(row => row.item_code === record.value?.item_code)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

function openEdit() {
  const r = record.value!
  Object.assign(edit, {
    daily_rate: String(r.daily_rate), replacement_value: String(r.replacement_value), deposit_required: String(r.deposit_required),
    prep_hours: String(r.prep_hours), total_quantity: String(r.total_quantity), required_accessories: r.required_accessories.join(', ')
  })
  editError.value = ''
  editOpen.value = true
}

async function saveEdit() {
  const r = record.value!
  const changes: Record<string, number | string> = {}
  for (const key of ['daily_rate', 'replacement_value', 'deposit_required', 'prep_hours'] as const) {
    if (Number(edit[key]) !== r[key]) changes[key] = Number(edit[key])
  }
  if (!r.is_serialized && Number(edit.total_quantity) !== r.total_quantity) changes.total_quantity = Number(edit.total_quantity)
  if (edit.required_accessories !== r.required_accessories.join(', ')) changes.required_accessories = edit.required_accessories
  if (!Object.keys(changes).length) return void (editOpen.value = false)
  saving.value = true
  editError.value = ''
  try {
    record.value = await getCortexApiClient().updateEquipmentProfile(r.item_code, changes)
    toast.create({ message: t('catalog.profile_saved'), type: 'success' })
    editOpen.value = false
  } catch (error) {
    editError.value = error instanceof Error ? error.message : String(error)
  } finally {
    saving.value = false
  }
}

watch(tab, value => { if (value === 'availability') void loadAvailability() })
watch(() => route.params.item, () => void load())
onMounted(load)
</script>
