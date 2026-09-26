<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.availability_matrix')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock' || provenance === 'demo'" :text="t('availability.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <TabButtons v-model="granularity" :buttons="granularityButtons" />
        <div class="flex items-center gap-1">
          <Button size="sm" variant="subtle" class="w-8" :aria-label="t('availability.previous')" @click="move(-1)">
            <template #icon><ChevronLeft class="size-4" :stroke-width="1.5" /></template>
          </Button>
          <Button size="sm" variant="subtle" @click="goToday">{{ t('availability.today') }}</Button>
          <Button size="sm" variant="subtle" class="w-8" :aria-label="t('availability.next')" @click="move(1)">
            <template #icon><ChevronRight class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </div>
        <Button v-if="session.hasPermission('cortex:quote:create')" size="sm" variant="solid" :disabled="!selected.length" @click="createQuote">
          {{ selected.length ? t('availability.create_quote_n', { count: selected.length }) : t('availability.create_quote') }}
        </Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('availability.filters')">
      <TextInput v-model="search" type="search" size="sm" variant="subtle" class="lg:col-span-2" :placeholder="t('availability.search')" :aria-label="t('availability.search')" />
      <Select
        :model-value="category"
        :options="categoryOptions"
        :placeholder="t('availability.category')"
        :aria-label="t('availability.category')"
        @update:model-value="(value: unknown) => (category = value === ANY ? undefined : String(value))"
      >
        <template #suffix><ChevronsUpDown class="ml-auto size-4 shrink-0 text-ink-gray-5" :stroke-width="1.5" /></template>
      </Select>
      <p class="flex h-7 items-center text-base text-ink-gray-7 lg:col-span-2">{{ rangeLabel }}</p>
    </PageFilters>

    <div v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-3" role="alert">
      <p class="text-base font-medium text-ink-red-4">{{ t('availability.load_failed') }}</p>
      <p class="mt-1 text-p-sm text-ink-gray-7">{{ errorMessage }}</p>
    </div>

    <div class="mt-6 flex min-h-0 flex-1">
      <div class="min-w-0 flex-1">
        <p v-if="loading && !rows.length" class="px-6 py-4 text-base text-ink-gray-5" role="status">{{ t('table.loading') }}</p>
        <AvailabilityGrid
          v-else
          v-model:selected="selected"
          :label="t('routes.availability_matrix')"
          :empty-text="t('availability.empty')"
          :rows="rows"
          :range-start="rangeStart"
          :range-end="rangeEnd"
          :granularity="granularity"
          @select-block="block => (selectedBlock = block)"
        />
        <p class="px-6 py-3 text-p-sm text-ink-gray-5">{{ t('availability.authority_note') }}</p>
      </div>

      <aside v-if="selectedBlock" class="w-[320px] shrink-0 border-l border-t border-outline-gray-1 px-4 py-4" :aria-label="t('availability.block_details')">
        <div class="flex items-start justify-between gap-2">
          <h2 class="text-base font-semibold text-ink-gray-9">{{ selectedBlock.rental_name }}</h2>
          <Button size="sm" variant="ghost" class="w-7" :aria-label="t('common.close')" @click="selectedBlock = null">
            <template #icon><X class="size-4" :stroke-width="1.5" /></template>
          </Button>
        </div>
        <dl class="mt-3 space-y-3 text-base">
          <div><dt class="text-sm text-ink-gray-5">{{ t('rentals.col_customer') }}</dt><dd>{{ selectedBlock.customer_name }}</dd></div>
          <div><dt class="text-sm text-ink-gray-5">{{ t('rentals.col_state') }}</dt><dd><RentalStateBadge :state="selectedBlock.state as RentalStateValue" /></dd></div>
          <div><dt class="text-sm text-ink-gray-5">{{ t('rental_detail.period') }}</dt><dd>{{ dateTime(selectedBlock.start_date) }} → {{ dateTime(selectedBlock.end_date) }}</dd></div>
          <div v-if="selectedBlock.is_conflict" class="rounded bg-surface-red-1 px-3 py-2 text-p-sm text-ink-red-4">{{ selectedBlock.conflict_reason || t('availability.conflict') }}</div>
        </dl>
        <Button class="mt-4 w-full" size="sm" variant="subtle" :route="{ name: 'rental-detail', params: { name: selectedBlock.rental_id } }">{{ t('availability.open_rental') }}</Button>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Select, TabButtons, TextInput, Tooltip } from 'frappe-ui'
import { ChevronLeft, ChevronRight, ChevronsUpDown, X } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import { getCortexApiClient } from '@/api'
import type { AvailabilityBlock, MatrixEquipmentRow } from '@/api/contracts/availability'
import type { RentalStateValue } from '@/api/contracts/rentals'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'
import RentalStateBadge from '@/features/rentals/components/RentalStateBadge.vue'
import AvailabilityGrid from '../components/AvailabilityGrid.vue'

type Granularity = 'day' | 'week' | 'month'
const ANY = '__any__'
// Options of Cortex Rental Item Profile.category (DocType JSON).
const CATEGORIES = ['Camera Bodies', 'Cinema Lenses', 'Lighting', 'Grip & Rigging', 'Audio', 'Monitors & Wireless Video', 'Power & Batteries']

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const granularity = ref<Granularity>((['day', 'week', 'month'] as const).find(value => value === route.query.view) ?? 'week')
const anchor = ref(typeof route.query.date === 'string' ? new Date(`${route.query.date}T00:00:00`) : new Date())
const search = ref('')
const category = ref<string | undefined>()
const rows = ref<MatrixEquipmentRow[]>([])
const provenance = ref<string | undefined>()
const loading = ref(false)
const errorMessage = ref('')
const selected = ref<string[]>([])
const selectedBlock = ref<AvailabilityBlock | null>(null)

const granularityButtons = computed(() => [
  { label: t('availability.granularity_day'), value: 'day' },
  { label: t('availability.granularity_week'), value: 'week' },
  { label: t('availability.granularity_month'), value: 'month' }
])
const categoryOptions = computed(() => [{ label: `${t('availability.category')} — ${t('finance.pnl.any')}`, value: ANY }, ...CATEGORIES.map(value => ({ label: value, value }))])

function startOf(date: Date, mode: Granularity) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  if (mode === 'week') d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  if (mode === 'month') d.setDate(1)
  return d
}
function shift(date: Date, mode: Granularity, amount: number) {
  const d = new Date(date)
  if (mode === 'month') d.setMonth(d.getMonth() + amount)
  else d.setDate(d.getDate() + amount * (mode === 'week' ? 7 : 1))
  return d
}
const pad = (n: number) => String(n).padStart(2, '0')
const ymd = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

const rangeStart = computed(() => startOf(anchor.value, granularity.value))
const rangeEnd = computed(() => shift(rangeStart.value, granularity.value, 1))
const rangeLabel = computed(() => {
  const fmt = new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'long', year: 'numeric' })
  const last = new Date(rangeEnd.value.getTime() - 1)
  return granularity.value === 'day' ? fmt.format(rangeStart.value) : `${fmt.format(rangeStart.value)} – ${fmt.format(last)}`
})
const dateTime = (value: string) => formatDateTime(value, locale.value as LocaleType)

function move(step: number) {
  anchor.value = shift(rangeStart.value, granularity.value, step)
}
function goToday() {
  anchor.value = new Date()
}

let sequence = 0
async function load() {
  const current = ++sequence
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().getAvailabilityMatrix({
      start_date: ymd(rangeStart.value),
      end_date: ymd(new Date(rangeEnd.value.getTime() - 1)),
      view_mode: granularity.value,
      category: category.value,
      search: search.value || undefined
    })
    if (current !== sequence) return
    rows.value = result.rows
    provenance.value = result.provenance
  } catch (error) {
    if (current === sequence) errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    if (current === sequence) loading.value = false
  }
}

function createQuote() {
  void router.push({ name: 'rental-composer', query: { items: selected.value.join(','), starts_at: ymd(rangeStart.value), ends_at: ymd(new Date(rangeEnd.value.getTime() - 1)) } })
}

let timer: ReturnType<typeof setTimeout> | undefined
watch([granularity, rangeStart, category], () => {
  void router.replace({ query: { view: granularity.value, date: ymd(rangeStart.value) } })
  void load()
})
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})
onMounted(load)
</script>
