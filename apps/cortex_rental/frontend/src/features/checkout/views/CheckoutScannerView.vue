<template>
  <RentalPicker
    v-if="!rentalId"
    :title="t('routes.checkout_scanner')"
    :hint="t('warehouse.checkout_pick_hint')"
    :empty-text="t('warehouse.checkout_pick_empty')"
    state="Contract"
    date-key="starts_at"
    @pick="name => router.push({ name: 'checkout-scanner', params: { rental: name } })"
  />

  <div v-else class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('warehouse.checkout_title', { name: rentalId })">
      <template #title-suffix>
        <RentalStateBadge v-if="rental" :state="rental.rental_state" size="md" />
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" :route="{ name: 'rental-detail', params: { name: rentalId } }">{{ t('warehouse.open_rental') }}</Button>
        <Button size="sm" variant="solid" :disabled="!canComplete" :loading="completing" @click="complete">{{ t('warehouse.complete_checkout') }}</Button>
      </template>
    </PageHeader>

    <p v-if="loadError" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ loadError }}</p>

    <template v-if="rental">
      <div v-if="rental.rental_state !== 'Contract'" class="mx-6 mt-4 rounded border border-outline-amber-1 bg-surface-amber-1 px-4 py-3 text-p-sm text-ink-amber-3" role="alert">
        {{ t('warehouse.checkout_wrong_state', { state: t(`rental_states.${rental.rental_state}`) }) }}
      </div>

      <section class="border-b border-outline-gray-1 px-6 py-5">
        <p class="mb-2 text-base text-ink-gray-6">{{ rental.customer_name }} · {{ dateTime(rental.starts_at) }} → {{ dateTime(rental.ends_at) }}</p>
        <ScanField
          :label="t('warehouse.scan_label')"
          :placeholder="t('warehouse.scan_checkout_placeholder')"
          :submit-label="t('warehouse.scan_submit')"
          :disabled="rental.rental_state !== 'Contract'"
          :on-scan="scan"
        />
        <div class="mt-3 flex items-center gap-3">
          <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-gray-2" role="progressbar" :aria-valuenow="scannedCount" :aria-valuemax="expectedCount" :aria-label="t('warehouse.progress')">
            <div class="h-full rounded-full bg-surface-gray-7 transition-[width]" :style="{ width: `${expectedCount ? (scannedCount / expectedCount) * 100 : 0}%` }" />
          </div>
          <span class="text-base tabular-nums text-ink-gray-7">{{ t('warehouse.progress_value', { done: scannedCount, total: expectedCount }) }}</span>
        </div>
        <p v-if="lastError" class="mt-2 text-p-sm text-ink-red-4" role="alert">{{ lastError }}</p>
      </section>

      <DataTable :label="t('warehouse.expected_serials')" :columns="columns" :rows="serialRows" row-key="serial" :filter-row="false" :empty-text="t('warehouse.no_serials')">
        <template #cell-status="{ row }">
          <Badge :theme="row.scanned ? 'green' : 'gray'" variant="subtle">{{ row.scanned ? t('warehouse.scanned') : t('warehouse.to_scan') }}</Badge>
        </template>
      </DataTable>
      <p v-if="bulkLines.length" class="px-6 py-3 text-p-sm text-ink-gray-5">
        {{ t('warehouse.bulk_lines', { lines: bulkLines.map(line => `${line.quantity} × ${line.item_name}`).join(', ') }) }}
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, toast } from 'frappe-ui'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { GetRentalResponse } from '@/api/contracts'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import RentalStateBadge from '@/features/rentals/components/RentalStateBadge.vue'
import RentalPicker from '@/features/warehouse/components/RentalPicker.vue'
import ScanField from '@/features/warehouse/components/ScanField.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const rentalId = computed(() => (typeof route.params.rental === 'string' ? route.params.rental : ''))
const rental = ref<GetRentalResponse | null>(null)
const loadError = ref('')
const lastError = ref('')
const completing = ref(false)

const dateTime = (value: string) => formatDateTime(value, locale.value as LocaleType)

interface SerialRow extends Record<string, unknown> { serial: string; item: string; scanned: boolean }
const serialRows = computed<SerialRow[]>(() =>
  (rental.value?.items ?? []).flatMap(line =>
    line.assigned_serials.map(serial => ({ serial, item: `${line.item_name} · ${line.item_code}`, scanned: line.scanned_checkout_serials.includes(serial) }))
  )
)
const bulkLines = computed(() => (rental.value?.items ?? []).filter(line => !line.assigned_serials.length))
const expectedCount = computed(() => serialRows.value.length)
const scannedCount = computed(() => serialRows.value.filter(row => row.scanned).length)
const canComplete = computed(() => rental.value?.rental_state === 'Contract' && scannedCount.value === expectedCount.value && !completing.value)

const columns = computed<DataTableColumn<SerialRow>[]>(() => [
  { key: 'serial', label: t('rental_detail.serial'), width: '220px' },
  { key: 'item', label: t('rental_detail.item') },
  { key: 'status', label: t('finance.invoices.state'), width: '160px', sortable: false }
])

async function load() {
  if (!rentalId.value) return
  loadError.value = ''
  try {
    rental.value = await getCortexApiClient().getRental({ id: rentalId.value })
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : String(error)
  }
}

async function scan(code: string): Promise<string | null> {
  lastError.value = ''
  try {
    const result = await getCortexApiClient().scanCheckoutSerial({ rental_id: rentalId.value, serial_number: code })
    if (result.status !== 'completed') throw new Error(result.errors?.[0]?.message ?? t('warehouse.scan_refused'))
    await load()
    return null
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
    return lastError.value
  }
}

async function complete() {
  completing.value = true
  try {
    const result = await getCortexApiClient().completeCheckout({ rental_id: rentalId.value })
    if (result.status !== 'completed') throw new Error(result.errors?.[0]?.message ?? t('warehouse.scan_refused'))
    toast.create({ message: t('warehouse.checkout_done', { name: rentalId.value }), type: 'success' })
    await router.push({ name: 'rental-detail', params: { name: rentalId.value } })
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
  } finally {
    completing.value = false
  }
}

watch(rentalId, () => {
  rental.value = null
  void load()
}, { immediate: true })
</script>
