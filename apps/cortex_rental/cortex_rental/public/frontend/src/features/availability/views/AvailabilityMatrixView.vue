<template>
  <div class="space-y-4 max-w-7xl mx-auto" data-test="screen-availability-matrix">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-cortex-border">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-xl font-bold text-cortex-text-primary tracking-tight">
            {{ t('routes.availability_matrix') }}
          </h1>
          <span class="px-2 py-0.5 rounded-full bg-cortex-primary-100 text-cortex-primary-800 text-[11px] font-semibold">
            Temps Réel
          </span>
          <span class="px-2 py-0.5 rounded-full bg-cortex-surface-secondary border border-cortex-border text-cortex-text-muted text-[11px] font-mono">
            DEMO
          </span>
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
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getCortexApiClient } from '@/api'
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
const dateLabel = ref<string>('8 sept. — 15 sept. 2026')

const rows = ref<MatrixEquipmentRow[]>([])
const isLoading = ref<boolean>(false)
const errorMessage = ref<string | null>(null)

const selectedEquipmentCodes = ref<string[]>([])
const selectedBlock = ref<AvailabilityBlock | null>(null)

const fetchMatrix = async () => {
  isLoading.value = true
  errorMessage.value = null
  try {
    const client = getCortexApiClient()
    const res = await client.getAvailabilityMatrix({
      start_date: '2026-09-08',
      end_date: '2026-09-15',
      view_mode: granularity.value,
      category: selectedCategory.value === 'all' ? undefined : selectedCategory.value,
      search: searchQuery.value ? searchQuery.value : undefined
    })
    rows.value = res.rows
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors du chargement de la matrice'
  } finally {
    isLoading.value = false
  }
}

const handleNavigate = (direction: 'prev' | 'next' | 'today') => {
  if (direction === 'today') {
    dateLabel.value = '8 sept. — 15 sept. 2026'
  } else if (direction === 'next') {
    dateLabel.value = '15 sept. — 22 sept. 2026'
  } else {
    dateLabel.value = '1 sept. — 8 sept. 2026'
  }
  fetchMatrix()
}

// Flow 2: Matrix → Quote navigation with prefilled query
const handleCreateQuote = () => {
  const itemsParam = selectedEquipmentCodes.value.join(',')
  router.push({
    path: '/app/cortex-rental/new',
    query: {
      items: itemsParam,
      starts_at: '2026-09-10',
      ends_at: '2026-09-17'
    }
  })
}

watch([granularity, selectedCategory], () => {
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
</script>
