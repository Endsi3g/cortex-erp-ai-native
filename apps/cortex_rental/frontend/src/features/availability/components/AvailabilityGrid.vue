<template>
  <!--
    Timeline grid. Blocks are positioned from their real start/end against
    the visible window (never by state), overlapping rentals are laid out
    in lanes so none hides another, and a conflict gets the 2px red border
    from the route map. Header/rows follow the ERPNext grid measurements.
  -->
  <div class="w-full overflow-x-auto border-t border-outline-gray-1">
    <div class="min-w-[900px]" role="grid" :aria-label="label" :aria-rowcount="rows.length + 1">
      <div class="sticky top-0 z-20 flex h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-base text-ink-gray-6" role="row">
        <div class="sticky left-0 z-30 flex w-[288px] shrink-0 items-center gap-2 border-r border-outline-gray-1 bg-surface-gray-2 px-[7.5px]" role="columnheader">
          <Checkbox :model-value="allSelected" :aria-label="t('availability.select_all')" @update:model-value="toggleAll" />
          {{ t('availability.equipment') }}
        </div>
        <div class="relative flex flex-1">
          <div
            v-for="column in columns"
            :key="column.key"
            class="flex flex-1 items-center justify-center border-r border-outline-gray-1 px-1 text-center last:border-r-0"
            :class="column.today ? 'text-ink-gray-9' : ''"
            role="columnheader"
          >
            <span class="truncate">{{ column.label }}</span>
          </div>
        </div>
      </div>

      <div v-if="!rows.length" class="px-4 py-8 text-center text-base text-ink-gray-5">{{ emptyText }}</div>

      <div
        v-for="row in laidOut"
        :key="row.item.item_code"
        class="flex border-b border-outline-gray-1"
        :style="{ minHeight: `${row.height}px` }"
        role="row"
      >
        <div class="sticky left-0 z-10 flex w-[288px] shrink-0 items-center gap-2 border-r border-outline-gray-1 bg-surface-white px-[7.5px] py-1.5" role="rowheader">
          <Checkbox
            :model-value="selected.includes(row.item.item_code)"
            :aria-label="t('availability.select_item', { item: row.item.item_name })"
            @update:model-value="toggle(row.item.item_code)"
          />
          <div class="min-w-0 flex-1">
            <p class="truncate text-base text-ink-gray-8" :title="row.item.item_name">{{ row.item.item_name }}</p>
            <p class="truncate text-sm text-ink-gray-5">{{ row.item.item_code }} · {{ row.item.category }}</p>
          </div>
          <span class="shrink-0 text-sm tabular-nums" :class="row.conflict ? 'text-ink-red-4' : 'text-ink-gray-6'" :title="t('availability.fleet_title')">
            {{ t('availability.fleet', { count: row.item.total_fleet }) }}
          </span>
        </div>
        <div class="relative flex flex-1" role="gridcell">
          <div v-for="column in columns" :key="column.key" class="flex-1 border-r border-outline-gray-1 last:border-r-0" :class="column.today ? 'bg-surface-gray-1' : ''" />
          <div v-if="nowOffset !== null" class="pointer-events-none absolute inset-y-0 w-px bg-surface-red-5" :style="{ left: `${nowOffset}%` }" aria-hidden="true" />
          <button
            v-for="placed in row.blocks"
            :key="placed.block.id"
            type="button"
            class="absolute flex h-[22px] items-center gap-1 overflow-hidden rounded px-1.5 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-4"
            :class="blockClass(placed.block)"
            :style="{ left: `${placed.left}%`, width: `${placed.width}%`, top: `${6 + placed.lane * 26}px` }"
            :title="blockTitle(placed.block)"
            :aria-label="blockTitle(placed.block)"
            @click="$emit('select-block', placed.block)"
          >
            <span v-if="placed.clippedStart" aria-hidden="true">‹</span>
            <span class="truncate">{{ placed.block.customer_name }} · {{ placed.block.rental_name }}</span>
            <span v-if="placed.clippedEnd" class="ml-auto" aria-hidden="true">›</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Checkbox } from 'frappe-ui'
import type { AvailabilityBlock, MatrixEquipmentRow } from '@/api/contracts/availability'
import { formatDateTime, parseFrappeDate } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

type Granularity = 'day' | 'week' | 'month'

const props = defineProps<{
  label: string
  emptyText: string
  rows: MatrixEquipmentRow[]
  rangeStart: Date
  rangeEnd: Date
  granularity: Granularity
  selected: string[]
}>()

const emit = defineEmits<{ 'select-block': [block: AvailabilityBlock]; 'update:selected': [codes: string[]] }>()
const { t, locale } = useI18n()

const span = computed(() => props.rangeEnd.getTime() - props.rangeStart.getTime())

const columns = computed(() => {
  const out: Array<{ key: string; label: string; today: boolean }> = []
  const loc = locale.value
  const today = new Date()
  if (props.granularity === 'day') {
    for (let hour = 0; hour < 24; hour += 4) {
      out.push({ key: `h${hour}`, label: `${String(hour).padStart(2, '0')} h`, today: false })
    }
    return out
  }
  const cursor = new Date(props.rangeStart)
  const fmt = new Intl.DateTimeFormat(loc, props.granularity === 'week' ? { weekday: 'short', day: 'numeric' } : { day: 'numeric' })
  while (cursor < props.rangeEnd) {
    out.push({ key: cursor.toISOString(), label: fmt.format(cursor), today: cursor.toDateString() === today.toDateString() })
    cursor.setDate(cursor.getDate() + 1)
  }
  return out
})

const nowOffset = computed(() => {
  const now = Date.now()
  if (now < props.rangeStart.getTime() || now > props.rangeEnd.getTime()) return null
  return ((now - props.rangeStart.getTime()) / span.value) * 100
})

function blocksOf(row: MatrixEquipmentRow): AvailabilityBlock[] {
  return [...(row.blocks ?? []), ...(row.serials ?? []).flatMap(serial => serial.blocks)]
}

/** Greedy lane assignment on real intervals; percentages against the visible window. */
const laidOut = computed(() =>
  props.rows.map(item => {
    const lanesEnd: number[] = []
    const blocks = blocksOf(item)
      .map(block => ({ block, start: parseFrappeDate(block.start_date).getTime(), end: parseFrappeDate(block.end_date).getTime() }))
      .filter(entry => entry.end > props.rangeStart.getTime() && entry.start < props.rangeEnd.getTime())
      .sort((a, b) => a.start - b.start)
      .map(entry => {
        let lane = lanesEnd.findIndex(end => end <= entry.start)
        if (lane === -1) {
          lane = lanesEnd.length
          lanesEnd.push(entry.end)
        } else {
          lanesEnd[lane] = entry.end
        }
        const from = Math.max(entry.start, props.rangeStart.getTime())
        const to = Math.min(entry.end, props.rangeEnd.getTime())
        return {
          block: entry.block,
          lane,
          left: ((from - props.rangeStart.getTime()) / span.value) * 100,
          width: Math.max(((to - from) / span.value) * 100, 1.5),
          clippedStart: entry.start < props.rangeStart.getTime(),
          clippedEnd: entry.end > props.rangeEnd.getTime()
        }
      })
    return {
      item,
      blocks,
      conflict: blocks.some(placed => placed.block.is_conflict),
      height: Math.max(52, 12 + Math.max(1, lanesEnd.length) * 26)
    }
  })
)

const STATE_CLASS: Record<string, string> = {
  Quote: 'border border-dashed border-outline-gray-3 bg-surface-white text-ink-gray-7',
  Reservation: 'border border-outline-blue-1 bg-surface-blue-2 text-ink-blue-3',
  Contract: 'border border-outline-blue-1 bg-surface-blue-2 text-ink-blue-3 font-medium',
  'Checked Out': 'border border-outline-amber-2 bg-surface-amber-2 text-ink-amber-3 font-medium',
  Quarantine: 'border border-outline-orange-1 bg-surface-orange-1 text-ink-gray-8'
}

function blockClass(block: AvailabilityBlock) {
  const base = STATE_CLASS[block.state] ?? 'border border-outline-gray-2 bg-surface-gray-2 text-ink-gray-7'
  return block.is_conflict ? `${base} !border-2 !border-outline-red-3` : base
}

function blockTitle(block: AvailabilityBlock) {
  const loc = locale.value as LocaleType
  return `${block.rental_name} · ${block.customer_name} · ${t(`rental_states.${block.state}`)} · ${formatDateTime(block.start_date, loc)} → ${formatDateTime(block.end_date, loc)}${block.is_conflict ? ` · ${t('availability.conflict')}` : ''}`
}

const allSelected = computed(() => props.rows.length > 0 && props.selected.length === props.rows.length)
function toggleAll() {
  emit('update:selected', allSelected.value ? [] : props.rows.map(row => row.item_code))
}
function toggle(code: string) {
  emit('update:selected', props.selected.includes(code) ? props.selected.filter(c => c !== code) : [...props.selected, code])
}
</script>
