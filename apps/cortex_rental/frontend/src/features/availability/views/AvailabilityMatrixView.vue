<template>
  <div class="space-y-4 max-w-7xl mx-auto" data-test="screen-availability-matrix">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-cortex-border">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-xl font-bold text-cortex-text-primary tracking-tight">
            {{ t('routes.availability_matrix') }}
          </h1>
          <Badge :theme="isSynthetic ? 'gray' : 'green'" variant="subtle">{{ isSynthetic ? 'Données de démo' : 'API ERPNext' }}</Badge>
        </div>
        <p class="text-xs text-cortex-text-secondary mt-1">
          Visualisation temporelle de l'inventaire, verrous de disponibilité et détection de conflits.
        </p>
      </div>

      <!-- Legend -->
      <AvailabilityLegend />
    </div>

    <!-- Toolbar -->
    <AvailabilityToolbar
      v-model:granularity="granularity"
      v-model:category="selectedCategory"
      v-model:search="searchQuery"
      :date-label="dateLabel"
      :selected-equipment-codes="selectedEquipmentCodes"
      @navigate="handleNavigate"
      @create-quote="handleCreateQuote"
    />

    <!-- Error Banner -->
    <CortexErrorBanner
      v-if="errorMessage"
      :error-message="errorMessage"
      @retry="fetchMatrix"
    />

    <!-- Main Grid or Loading Skeleton -->
    <div v-if="isLoading" class="p-6 bg-cortex-surface rounded-xl border border-cortex-border">
      <CortexSkeleton :lines="12" />
    </div>

    <div v-else class="space-y-4">
      <!-- Matrix Grid -->
      <AvailabilityGrid
        :rows="rows"
        :granularity="granularity"
        v-model:selected-equipment-codes="selectedEquipmentCodes"
        @select-block="selectedBlock = $event"
      />

      <!-- Selected Block Inspector (Card below grid) -->
      <AvailabilityBlockInspector
        :block="selectedBlock"
        @close="selectedBlock = null"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge } from 'frappe-ui'
import { getCortexApiClient } from '@/api'
import { MockCortexApiClient } from '@/api/mock/MockCortexApiClient'
import type { MatrixEquipmentRow, AvailabilityBlock } from '@/api/contracts/availability'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import AvailabilityLegend from '../components/AvailabilityLegend.vue'
import AvailabilityToolbar from '../components/AvailabilityToolbar.vue'
import AvailabilityGrid from '../components/AvailabilityGrid.vue'
import AvailabilityBlockInspector from '../components/AvailabilityBlockInspector.vue'

const { t } = useI18n()
const router = useRouter()

const granularity = ref<'day' | 'week' | 'month'>('week')
const selectedCategory = ref<string>('all')
const searchQuery = ref<string>('')
const visibleStart = ref(startOfRange(new Date(), granularity.value))
const visibleEnd = computed(() => addRange(visibleStart.value, granularity.value, 1))
const dateLabel = computed(() => {
  const inclusiveEnd = new Date(visibleEnd.value.getTime() - 24 * 60 * 60 * 1000)
  const format = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  return granularity.value === 'day' ? format.format(visibleStart.value) : `${format.format(visibleStart.value)} — ${format.format(inclusiveEnd)}`
})

const rows = ref<MatrixEquipmentRow[]>([])
const isLoading = ref<boolean>(false)
const errorMessage = ref<string | null>(null)
const isSynthetic = ref(true)
let requestVersion = 0

const selectedEquipmentCodes = ref<string[]>([])
const selectedBlock = ref<AvailabilityBlock | null>(null)

const fetchMatrix = async () => {
  const requestId = ++requestVersion
  isLoading.value = true
  errorMessage.value = null
  try {
    const client = getCortexApiClient()
    isSynthetic.value = client instanceof MockCortexApiClient
    const res = await client.getAvailabilityMatrix({
      start_date: toDateParam(visibleStart.value),
      end_date: toDateParam(visibleEnd.value),
      view_mode: granularity.value,
      category: selectedCategory.value === 'all' ? undefined : selectedCategory.value,
      search: searchQuery.value ? searchQuery.value : undefined
    })
    if (requestId === requestVersion) rows.value = res.rows
  } catch (err: unknown) {
    if (requestId === requestVersion) errorMessage.value = err instanceof Error ? err.message : 'Erreur lors du chargement de la matrice'
  } finally {
    if (requestId === requestVersion) isLoading.value = false
  }
}

const handleNavigate = (direction: 'prev' | 'next' | 'today') => {
  visibleStart.value = direction === 'today'
    ? startOfRange(new Date(), granularity.value)
    : addRange(visibleStart.value, granularity.value, direction === 'next' ? 1 : -1)
}

// Flow 2: Matrix → Quote navigation with prefilled query
const handleCreateQuote = () => {
  const itemsParam = selectedEquipmentCodes.value.join(',')
  router.push({
    path: '/rentals/new',
    query: {
      items: itemsParam,
      starts_at: toDateParam(visibleStart.value),
      ends_at: toDateParam(visibleEnd.value)
    }
  })
}

watch(granularity, (value) => {
  visibleStart.value = startOfRange(visibleStart.value, value)
})

watch([granularity, selectedCategory, visibleStart], () => {
  fetchMatrix()
})

let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    fetchMatrix()
  }, 250)
})

onMounted(() => {
  fetchMatrix()
})

function startOfRange(input: Date, mode: 'day' | 'week' | 'month') {
  const date = new Date(input)
  date.setHours(0, 0, 0, 0)
  if (mode === 'month') date.setDate(1)
  if (mode === 'week') date.setDate(date.getDate() - ((date.getDay() + 6) % 7))
  return date
}

function addRange(input: Date, mode: 'day' | 'week' | 'month', amount: number) {
  const date = new Date(input)
  if (mode === 'month') date.setMonth(date.getMonth() + amount)
  else date.setDate(date.getDate() + amount * (mode === 'week' ? 7 : 1))
  return date
}

function toDateParam(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
</script>
