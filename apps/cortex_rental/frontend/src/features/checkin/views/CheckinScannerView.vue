<template>
  <RentalPicker
    v-if="!rentalId"
    :title="t('routes.checkin_scanner')"
    :hint="t('warehouse.checkin_pick_hint')"
    :empty-text="t('warehouse.checkin_pick_empty')"
    state="Checked Out"
    date-key="ends_at"
    @pick="name => router.push({ name: 'checkin-scanner', params: { rental: name } })"
  />

  <div v-else class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('warehouse.checkin_title', { name: rentalId })">
      <template #title-suffix>
        <RentalStateBadge v-if="rental" :state="rental.rental_state" size="md" />
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" :route="{ name: 'rental-detail', params: { name: rentalId } }">{{ t('warehouse.open_rental') }}</Button>
        <Button size="sm" variant="solid" :disabled="!canSubmit" :loading="submitting" @click="submit">{{ t('warehouse.submit_checkin') }}</Button>
      </template>
    </PageHeader>

    <p v-if="loadError" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ loadError }}</p>

    <template v-if="rental">
      <div v-if="rental.rental_state !== 'Checked Out'" class="mx-6 mt-4 rounded border border-outline-amber-1 bg-surface-amber-1 px-4 py-3 text-p-sm text-ink-amber-3" role="alert">
        {{ t('warehouse.checkin_wrong_state', { state: t(`rental_states.${rental.rental_state}`) }) }}
      </div>

      <section class="border-b border-outline-gray-1 px-6 py-5">
        <p class="mb-2 text-base text-ink-gray-6">{{ rental.customer_name }} · {{ t('warehouse.due') }} {{ dateTime(rental.ends_at) }}</p>
        <ScanField
          :label="t('warehouse.scan_label')"
          :placeholder="t('warehouse.scan_checkin_placeholder')"
          :submit-label="t('warehouse.scan_submit')"
          :disabled="rental.rental_state !== 'Checked Out'"
          :on-scan="scan"
        />
        <div class="mt-3 flex items-center gap-3">
          <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-gray-2" role="progressbar" :aria-valuenow="receivedCount" :aria-valuemax="serials.length" :aria-label="t('warehouse.progress')">
            <div class="h-full rounded-full bg-surface-gray-7 transition-[width]" :style="{ width: `${serials.length ? (receivedCount / serials.length) * 100 : 0}%` }" />
          </div>
          <span class="text-base tabular-nums text-ink-gray-7">{{ t('warehouse.progress_value', { done: receivedCount, total: serials.length }) }}</span>
        </div>
        <p v-if="lastError" class="mt-2 text-p-sm text-ink-red-4" role="alert">{{ lastError }}</p>
      </section>

      <!-- Serialized units -->
      <div class="overflow-x-auto">
        <table class="w-full min-w-max border-collapse text-base text-ink-gray-8" :aria-label="t('warehouse.units')">
          <thead>
            <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
              <th class="w-[37px] border-r border-outline-gray-1 font-normal"><span class="sr-only">#</span></th>
              <th class="border-r border-outline-gray-1 px-[7.5px] text-left font-normal">{{ t('rental_detail.item') }}</th>
              <th class="w-[180px] border-r border-outline-gray-1 px-[7.5px] text-left font-normal">{{ t('rental_detail.serial') }}</th>
              <th class="w-[130px] border-r border-outline-gray-1 px-[7.5px] text-left font-normal">{{ t('warehouse.reception') }}</th>
              <th class="w-[170px] border-r border-outline-gray-1 px-[7.5px] text-left font-normal">{{ t('warehouse.condition') }}</th>
              <th class="w-[190px] px-[7.5px] text-left font-normal">{{ t('warehouse.disposition') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!serials.length" class="h-[33px]"><td colspan="6" class="px-4 py-6 text-center text-ink-gray-5">{{ t('warehouse.no_serials') }}</td></tr>
            <template v-for="(unit, index) in serials" :key="unit.serial">
              <tr class="h-[33px] border-b border-outline-gray-1" :class="unit.alreadyReturned ? 'text-ink-gray-5' : ''">
                <td class="border-r border-outline-gray-1 text-center tabular-nums">{{ index + 1 }}</td>
                <td class="border-r border-outline-gray-1 px-[7.5px]">{{ unit.itemName }}</td>
                <td class="border-r border-outline-gray-1 px-[7.5px]">{{ unit.serial }}</td>
                <td class="border-r border-outline-gray-1 px-[7.5px]">
                  <Badge v-if="unit.alreadyReturned" theme="gray" variant="subtle">{{ t('warehouse.already_returned') }}</Badge>
                  <Badge v-else-if="unit.received" theme="green" variant="subtle">{{ t('warehouse.received') }}</Badge>
                  <Badge v-else-if="unit.condition === 'Missing'" theme="red" variant="subtle">{{ t('warehouse.missing') }}</Badge>
                  <Badge v-else theme="gray" variant="subtle">{{ t('warehouse.pending') }}</Badge>
                </td>
                <td class="border-r border-outline-gray-1 px-1">
                  <select v-if="!unit.alreadyReturned" v-model="unit.condition" class="h-6 w-full rounded border-0 bg-surface-gray-2 py-0 pl-1.5 text-base focus:ring-1 focus:ring-outline-gray-3" :aria-label="t('warehouse.condition_for', { serial: unit.serial })" @change="onConditionChange(unit)">
                    <option v-for="value in CONDITIONS" :key="value" :value="value">{{ t(`warehouse.condition_${value}`) }}</option>
                  </select>
                </td>
                <td class="px-1">
                  <select v-if="!unit.alreadyReturned" v-model="unit.disposition" class="h-6 w-full rounded border-0 bg-surface-gray-2 py-0 pl-1.5 text-base focus:ring-1 focus:ring-outline-gray-3" :aria-label="t('warehouse.disposition_for', { serial: unit.serial })">
                    <option v-for="value in DISPOSITIONS" :key="value" :value="value">{{ t(`warehouse.disposition_${value.replace(/[ -]/g, '_')}`) }}</option>
                  </select>
                </td>
              </tr>
              <tr v-if="unit.condition === 'Damaged' && !unit.alreadyReturned" class="border-b border-outline-gray-1 bg-surface-gray-1">
                <td />
                <td colspan="5" class="px-[7.5px] py-3">
                  <div class="grid grid-cols-1 gap-3 md:grid-cols-4">
                    <FormControl v-model="unit.severity" type="select" size="sm" variant="subtle" :label="t('warehouse.severity')" :options="SEVERITIES.map(value => ({ label: t(`warehouse.severity_${value}`), value }))" />
                    <FormControl v-model="unit.damageType" type="select" size="sm" variant="subtle" :label="t('warehouse.damage_type')" :options="DAMAGE_TYPES.map(value => ({ label: t(`warehouse.damage_${value.replace(/[^A-Za-z]/g, '')}`), value }))" />
                    <FormControl v-model="unit.repairCost" type="number" size="sm" variant="subtle" :label="t('warehouse.repair_cost')" />
                    <div>
                      <p class="mb-1.5 text-sm text-ink-gray-5">{{ t('warehouse.evidence') }}</p>
                      <label class="inline-flex h-7 cursor-pointer items-center gap-2 rounded bg-surface-gray-2 px-2 text-base hover:bg-surface-gray-3">
                        <Camera class="size-4" :stroke-width="1.5" aria-hidden="true" />
                        <span class="truncate">{{ unit.fileLabel || t('warehouse.add_photo') }}</span>
                        <input type="file" accept="image/*" capture="environment" class="sr-only" @change="event => attachPhoto(unit, event)" />
                      </label>
                    </div>
                  </div>
                  <FormControl v-model="unit.notes" type="textarea" size="sm" variant="subtle" class="mt-3" :label="t('warehouse.damage_notes')" />
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Bulk (non-serialized) lines -->
      <section v-if="bulk.length" class="px-6 py-5">
        <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('warehouse.bulk_title') }}</h2>
        <div v-for="line in bulk" :key="line.id" class="flex items-center gap-4 border-b border-outline-gray-1 py-2 text-base">
          <span class="min-w-0 flex-1 truncate">{{ line.itemName }}</span>
          <span class="text-ink-gray-5">{{ t('warehouse.expected', { qty: line.expected }) }}</span>
          <FormControl v-model="line.returned" type="number" size="sm" variant="subtle" class="w-24" :aria-label="t('warehouse.returned_for', { item: line.itemName })" />
        </div>
      </section>

      <!-- Finalisation -->
      <section class="grid grid-cols-1 gap-6 border-t border-outline-gray-1 px-6 py-5 lg:grid-cols-2">
        <fieldset>
          <legend class="mb-2 text-base font-semibold text-ink-gray-9">{{ t('warehouse.finalize') }}</legend>
          <label v-for="mode in MODES" :key="mode" class="flex cursor-pointer items-start gap-2 py-1 text-base">
            <input v-model="finalizeMode" type="radio" name="finalize" :value="mode" class="mt-1 text-ink-gray-9 focus:ring-outline-gray-3" />
            <span><span class="text-ink-gray-8">{{ t(`warehouse.mode_${mode}`) }}</span><span class="block text-sm text-ink-gray-5">{{ t(`warehouse.mode_${mode}_hint`) }}</span></span>
          </label>
        </fieldset>
        <div>
          <FormControl v-model="notes" type="textarea" size="sm" variant="subtle" :label="t('warehouse.checkin_notes')" />
          <p class="mt-3 text-p-sm text-ink-gray-5">{{ summary }}</p>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, FormControl, toast } from 'frappe-ui'
import { Camera } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import { getCortexApiClient } from '@/api'
import type { CompletePartialReturnInput, GetRentalResponse } from '@/api/contracts'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import RentalStateBadge from '@/features/rentals/components/RentalStateBadge.vue'
import RentalPicker from '@/features/warehouse/components/RentalPicker.vue'
import ScanField from '@/features/warehouse/components/ScanField.vue'

type Item = NonNullable<CompletePartialReturnInput['items']>[number]
const CONDITIONS = ['Good', 'Damaged', 'Missing'] as const
const DISPOSITIONS = ['Return to Stock', 'Quarantine', 'Repair', 'Missing', 'Write-off'] as const
const SEVERITIES = ['Cosmetic', 'Functional', 'Blocking'] as const
const DAMAGE_TYPES = ['Physical / Impact', 'Optical Scratch', 'Electronic Failure', 'Liquid / Moisture', 'Cable / Connector', 'Missing Parts', 'Other'] as const
const MODES = ['auto', 'partial', 'settle_with_loss'] as const

interface Unit {
  lineId: string
  itemCode: string
  itemName: string
  serial: string
  alreadyReturned: boolean
  received: boolean
  condition: (typeof CONDITIONS)[number]
  disposition: (typeof DISPOSITIONS)[number]
  severity: string
  damageType: string
  repairCost: string
  notes: string
  fileName?: string
  fileLabel?: string
}
interface BulkLine { id: string; itemCode: string; itemName: string; expected: number; returned: string }

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const rentalId = computed(() => (typeof route.params.rental === 'string' ? route.params.rental : ''))
const rental = ref<GetRentalResponse | null>(null)
const serials = ref<Unit[]>([])
const bulk = ref<BulkLine[]>([])
const finalizeMode = ref<(typeof MODES)[number]>('auto')
const notes = ref('')
const loadError = ref('')
const lastError = ref('')
const submitting = ref(false)

const dateTime = (value: string) => formatDateTime(value, locale.value as LocaleType)
const receivedCount = computed(() => serials.value.filter(unit => unit.received || unit.alreadyReturned).length)

function reset(value: GetRentalResponse) {
  serials.value = value.items.flatMap(line =>
    line.assigned_serials.map(serial => reactive<Unit>({
      lineId: line.id, itemCode: line.item_code, itemName: line.item_name, serial,
      alreadyReturned: line.scanned_checkin_serials.includes(serial), received: false,
      condition: 'Good', disposition: 'Return to Stock', severity: 'Cosmetic', damageType: 'Physical / Impact', repairCost: '', notes: ''
    }))
  )
  bulk.value = value.items
    .filter(line => !line.assigned_serials.length)
    .map(line => reactive({ id: line.id, itemCode: line.item_code, itemName: line.item_name, expected: line.quantity, returned: String(line.quantity) }))
}

async function load() {
  if (!rentalId.value) return
  loadError.value = ''
  try {
    rental.value = await getCortexApiClient().getRental({ id: rentalId.value })
    reset(rental.value)
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : String(error)
  }
}

async function scan(code: string): Promise<string | null> {
  lastError.value = ''
  const unit = serials.value.find(candidate => candidate.serial === code)
  if (unit?.alreadyReturned) return (lastError.value = t('warehouse.already_returned_error', { serial: code }))
  try {
    await getCortexApiClient().scanCheckinSerial({ rental_id: rentalId.value, serial_number: code, condition: 'Good' })
    if (!unit) return (lastError.value = t('warehouse.not_on_rental', { serial: code }))
    unit.received = true
    if (unit.condition === 'Missing') unit.condition = 'Good'
    return null
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
    return lastError.value
  }
}

function onConditionChange(unit: Unit) {
  if (unit.condition === 'Missing') {
    unit.received = false
    unit.disposition = 'Missing'
  } else if (unit.condition === 'Damaged') {
    unit.disposition = 'Quarantine'
  } else if (unit.disposition === 'Missing' || unit.disposition === 'Quarantine') {
    unit.disposition = 'Return to Stock'
  }
}

async function attachPhoto(unit: Unit, event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  unit.fileLabel = t('warehouse.uploading')
  try {
    const uploaded = await getCortexApiClient().uploadRentalEvidence(rentalId.value, file)
    unit.fileName = uploaded.file_name
    unit.fileLabel = file.name
  } catch (error) {
    unit.fileLabel = undefined
    lastError.value = error instanceof Error ? error.message : String(error)
  }
}

/** What will be sent: received units, explicitly missing ones, and (settle with loss) every unit still out. */
const payload = computed<Item[]>(() => {
  const units = serials.value.filter(unit => !unit.alreadyReturned)
  const items: Item[] = []
  for (const unit of units) {
    const missing = unit.condition === 'Missing' || (!unit.received && finalizeMode.value === 'settle_with_loss')
    if (!unit.received && !missing) continue
    items.push({
      transaction_item: unit.lineId,
      item_code: unit.itemCode,
      serial_no: unit.serial,
      expected_qty: 1,
      returned_qty: missing ? 0 : 1,
      condition: missing ? 'Missing' : unit.condition,
      disposition: missing ? (unit.disposition === 'Write-off' ? 'Write-off' : 'Missing') : unit.disposition,
      damage_severity: unit.condition === 'Damaged' ? (unit.severity as Item['damage_severity']) : 'None',
      damage_type: unit.condition === 'Damaged' ? (unit.damageType as Item['damage_type']) : 'None',
      estimated_repair_cost: unit.condition === 'Damaged' && unit.repairCost ? Number(unit.repairCost) : undefined,
      notes: unit.notes || undefined,
      file_name: unit.fileName
    })
  }
  for (const line of bulk.value) {
    const returned = Math.max(0, Math.min(line.expected, Number(line.returned) || 0))
    items.push({ transaction_item: line.id, item_code: line.itemCode, expected_qty: line.expected, returned_qty: returned, condition: returned < line.expected ? 'Missing' : 'Good', disposition: returned < line.expected ? 'Missing' : 'Return to Stock', damage_severity: 'None', damage_type: 'None' })
  }
  return items
})

const pendingCount = computed(() => serials.value.filter(unit => !unit.alreadyReturned && !unit.received && unit.condition !== 'Missing').length)
const summary = computed(() => {
  if (finalizeMode.value === 'settle_with_loss' && pendingCount.value) return t('warehouse.summary_loss', { count: pendingCount.value })
  if (pendingCount.value) return t('warehouse.summary_partial', { count: pendingCount.value })
  return t('warehouse.summary_full')
})

const canSubmit = computed(() => rental.value?.rental_state === 'Checked Out' && payload.value.length > 0 && !submitting.value)

async function submit() {
  submitting.value = true
  lastError.value = ''
  try {
    const result = await getCortexApiClient().completePartialReturn({ rental_id: rentalId.value, items: payload.value, notes: notes.value || undefined, finalize_mode: finalizeMode.value })
    if (result.status !== 'completed') throw new Error(result.errors?.[0]?.message ?? t('warehouse.scan_refused'))
    toast.create({ message: t('warehouse.checkin_done', { name: rentalId.value }), type: 'success' })
    await router.push({ name: 'rental-detail', params: { name: rentalId.value }, query: { tab: 'billing' } })
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
  } finally {
    submitting.value = false
  }
}

watch(rentalId, () => {
  rental.value = null
  void load()
}, { immediate: true })
</script>
