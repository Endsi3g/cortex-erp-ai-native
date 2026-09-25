<template>
  <div
    class="rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs overflow-hidden flex flex-col"
    data-test="availability-grid"
  >
    <!-- Scrollable container -->
    <div
      ref="containerRef"
      class="overflow-x-auto overflow-y-auto max-h-[600px] relative scrollbar-thin"
      @scroll="handleScroll"
    >
      <!-- Matrix Header -->
      <div class="flex items-stretch border-b border-cortex-border bg-cortex-surface-secondary sticky top-0 z-30 min-w-max">
        <!-- Sticky Equipment Column Header (288px) -->
        <div
          class="w-[288px] min-w-[288px] sticky left-0 z-40 bg-cortex-surface-secondary px-3.5 py-3 border-r border-cortex-border flex items-center justify-between shadow-xs"
          data-test="sticky-equipment-column-header"
        >
          <div class="flex items-center gap-2">
            <input
              type="checkbox"
              :checked="isAllSelected"
              class="rounded border-cortex-border text-cortex-primary-600 focus:ring-cortex-primary-500 w-3.5 h-3.5 cursor-pointer"
              title="Sélectionner tous"
              @change="toggleSelectAll"
            />
            <span class="text-xs font-bold uppercase tracking-wider text-cortex-text-primary">
              {{ t('availability.equipment_column') }}
            </span>
          </div>
          <span class="text-[11px] font-mono text-cortex-text-muted">
            {{ rows.length }}
          </span>
        </div>

        <!-- Time Slot Columns Header -->
        <div class="flex flex-1">
          <div
            v-for="col in timeColumns"
            :key="col.id"
            class="min-w-[120px] flex-1 px-2.5 py-3 border-r border-cortex-border text-center flex flex-col items-center justify-center"
            :data-test="`column-header-${col.id}`"
          >
            <span class="text-xs font-semibold text-cortex-text-primary font-mono">{{ col.label }}</span>
            <span v-if="col.sublabel" class="text-[10px] text-cortex-text-muted">{{ col.sublabel }}</span>
          </div>
        </div>
      </div>

      <!-- Virtualized Rows Container -->
      <div
        class="relative min-w-max"
        :style="{ height: `${virtualTotalHeight}px` }"
        data-test="virtual-grid-container"
      >
        <div
          class="absolute left-0 right-0 top-0"
          :style="{ transform: `translateY(${virtualOffsetY}px)` }"
        >
          <div
            v-for="virtualRow in virtualRows"
            :key="virtualRow.item.item_code"
            class="flex items-stretch border-b border-cortex-border/70 hover:bg-cortex-bg-secondary/30 transition-colors min-h-[52px]"
            :data-test="`matrix-row-${virtualRow.item.item_code}`"
          >
            <!-- Sticky Equipment Column (288px) -->
            <div
              class="w-[288px] min-w-[288px] sticky left-0 z-20 bg-cortex-surface px-3.5 py-2.5 border-r border-cortex-border flex items-center justify-between gap-2 shadow-xs"
              data-test="sticky-equipment-cell"
            >
              <div class="flex items-center gap-2.5 min-w-0">
                <input
                  type="checkbox"
                  :checked="selectedEquipmentCodes.includes(virtualRow.item.item_code)"
                  class="rounded border-cortex-border text-cortex-primary-600 focus:ring-cortex-primary-500 w-3.5 h-3.5 cursor-pointer flex-shrink-0"
                  :data-test="`select-item-${virtualRow.item.item_code}`"
                  @change="toggleSelectEquipment(virtualRow.item.item_code)"
                />
                <div class="min-w-0">
                  <span class="text-xs font-semibold text-cortex-text-primary truncate block" :title="virtualRow.item.item_name">
                    {{ virtualRow.item.item_name }}
                  </span>
                  <div class="flex items-center gap-1.5 mt-0.5">
                    <span class="text-[10px] font-mono text-cortex-primary-700 bg-cortex-primary-50 px-1 rounded">
                      {{ virtualRow.item.item_code }}
                    </span>
                    <span class="text-[10px] text-cortex-text-muted">
                      {{ virtualRow.item.category }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Serials count badge or toggle -->
              <span
                v-if="virtualRow.item.serials && virtualRow.item.serials.length > 0"
                class="px-1.5 py-0.5 rounded bg-cortex-surface-secondary text-[10px] font-mono text-cortex-text-muted border border-cortex-border flex-shrink-0"
              >
                {{ virtualRow.item.serials.length }} sn
              </span>
            </div>

            <!-- Time Slot Cells & Availability Blocks -->
            <div class="flex flex-1 relative min-h-[52px]">
              <!-- Grid background slot cells -->
              <div
                v-for="col in timeColumns"
                :key="col.id"
                class="min-w-[120px] flex-1 border-r border-cortex-border/40"
              />

              <!-- Overlay Blocks for this row -->
              <div
                v-for="block in getRowBlocks(virtualRow.item)"
                :key="block.id"
                class="absolute top-1 bottom-1 rounded px-2 py-1 flex items-center justify-between text-xs cursor-pointer select-none transition-all hover:brightness-95 shadow-2xs overflow-hidden"
                :class="getBlockClass(block)"
                :style="getBlockStyle(block)"
                :title="block.is_conflict ? `CONFLIT: ${block.conflict_reason}` : `${block.rental_name} (${block.customer_name})`"
                :data-test="`availability-block-${block.id}`"
                @click.stop="emit('select-block', block)"
                @dblclick.stop="navigateToRental(block.rental_id)"
              >
                <div class="flex items-center gap-1 truncate">
                  <AlertTriangle v-if="block.is_conflict" class="w-3.5 h-3.5 text-red-600 flex-shrink-0 animate-pulse" />
                  <span class="font-mono font-bold text-[11px] truncate">{{ block.rental_name }}</span>
                  <span class="text-[10px] opacity-85 truncate hidden sm:inline">- {{ block.customer_name }}</span>
                </div>
                <span class="text-[10px] uppercase font-bold tracking-wider px-1 rounded opacity-90 ml-1">
                  {{ block.state }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, toRef } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { AlertTriangle } from 'lucide-vue-next'
import type { MatrixEquipmentRow, AvailabilityBlock } from '@/api/contracts/availability'
import { useVirtualMatrix } from '../composables/useVirtualMatrix'

const { t } = useI18n()
const router = useRouter()

const props = withDefaults(
  defineProps<{
    rows: MatrixEquipmentRow[]
    granularity: 'day' | 'week' | 'month'
    selectedEquipmentCodes: string[]
  }>(),
  {
    rows: () => [],
    granularity: 'week',
    selectedEquipmentCodes: () => []
  }
)

const emit = defineEmits<{
  (e: 'update:selectedEquipmentCodes', val: string[]): void
  (e: 'select-block', block: AvailabilityBlock): void
}>()

const containerRef = ref<HTMLElement | null>(null)
const viewportHeight = ref(540)
const rowHeight = 56

const rowsRef = toRef(props, 'rows')

const {
  totalHeight: virtualTotalHeight,
  visibleItems: virtualRows,
  offsetY: virtualOffsetY,
  onScroll: handleScroll
} = useVirtualMatrix({
  items: rowsRef,
  rowHeight,
  viewportHeight,
  overscan: 4
})

// Time columns based on granularity
const timeColumns = computed(() => {
  if (props.granularity === 'day') {
    return [
      { id: 't-08', label: '08:00', sublabel: 'Matin' },
      { id: 't-12', label: '12:00', sublabel: 'Midi' },
      { id: 't-16', label: '16:00', sublabel: 'Après-midi' },
      { id: 't-20', label: '20:00', sublabel: 'Soir' }
    ]
  }
  if (props.granularity === 'month') {
    return Array.from({ length: 15 }, (_, i) => ({
      id: `m-${i + 1}`,
      label: `J+${i + 1}`,
      sublabel: 'Sept'
    }))
  }
  // Default: week (7 days)
  return [
    { id: 'w-1', label: 'Lun 08', sublabel: 'Septembre' },
    { id: 'w-2', label: 'Mar 09', sublabel: 'Septembre' },
    { id: 'w-3', label: 'Mer 10', sublabel: 'Septembre' },
    { id: 'w-4', label: 'Jeu 11', sublabel: 'Septembre' },
    { id: 'w-5', label: 'Ven 12', sublabel: 'Septembre' },
    { id: 'w-6', label: 'Sam 13', sublabel: 'Septembre' },
    { id: 'w-7', label: 'Dim 14', sublabel: 'Septembre' }
  ]
})

const isAllSelected = computed(() => {
  return props.rows.length > 0 && props.selectedEquipmentCodes.length === props.rows.length
})

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    emit('update:selectedEquipmentCodes', [])
  } else {
    emit('update:selectedEquipmentCodes', props.rows.map(r => r.item_code))
  }
}

const toggleSelectEquipment = (code: string) => {
  if (props.selectedEquipmentCodes.includes(code)) {
    emit('update:selectedEquipmentCodes', props.selectedEquipmentCodes.filter(c => c !== code))
  } else {
    emit('update:selectedEquipmentCodes', [...props.selectedEquipmentCodes, code])
  }
}

const getRowBlocks = (item: MatrixEquipmentRow): AvailabilityBlock[] => {
  const blocks: AvailabilityBlock[] = []
  if (item.blocks) {
    blocks.push(...item.blocks)
  }
  if (item.serials) {
    for (const s of item.serials) {
      if (s.blocks) {
        blocks.push(...s.blocks)
      }
    }
  }
  return blocks
}

// 2px red border conflict styling rule and state classes
const getBlockClass = (block: AvailabilityBlock) => {
  if (block.is_conflict) {
    return 'border-2 border-red-600 bg-red-50 text-red-900 font-bold z-10 shadow-xs'
  }
  switch (block.state) {
    case 'Quote':
      return 'border-2 border-dashed border-gray-400 bg-gray-50/80 text-gray-700'
    case 'Reservation':
      return 'border border-amber-400 bg-amber-100 text-amber-900 font-medium'
    case 'Contract':
      return 'border border-blue-400 bg-blue-100 text-blue-900 font-medium'
    case 'Checked Out':
      return 'border border-purple-400 bg-purple-100 text-purple-900 font-medium'
    case 'Quarantine':
      return 'border border-red-300 bg-red-100 text-red-900 font-medium'
    default:
      return 'border border-gray-300 bg-gray-100 text-gray-800'
  }
}

const getBlockStyle = (block: AvailabilityBlock) => {
  // Horizontal positioning across the time grid
  const colsCount = timeColumns.value.length
  const colWidthPct = 100 / colsCount

  let startIndex = 0
  let span = 2

  if (block.state === 'Checked Out') {
    startIndex = 0
    span = props.granularity === 'day' ? 2 : 4
  } else if (block.state === 'Contract') {
    startIndex = props.granularity === 'day' ? 1 : 2
    span = props.granularity === 'day' ? 3 : 4
  } else if (block.state === 'Reservation') {
    startIndex = props.granularity === 'day' ? 2 : 3
    span = props.granularity === 'day' ? 2 : 3
  } else if (block.state === 'Quote') {
    startIndex = props.granularity === 'day' ? 1 : 4
    span = 2
  } else if (block.state === 'Quarantine') {
    startIndex = 0
    span = 3
  }

  const left = Math.min(100, startIndex * colWidthPct)
  const width = Math.min(100 - left, span * colWidthPct)

  return {
    left: `${left}%`,
    width: `${Math.max(width, 18)}%`
  }
}

const navigateToRental = (rentalId: string) => {
  router.push(`/rentals/${rentalId}`)
}
</script>
