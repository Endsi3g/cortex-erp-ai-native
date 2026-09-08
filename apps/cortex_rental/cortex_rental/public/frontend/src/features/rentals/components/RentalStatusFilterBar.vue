<template>
  <div class="flex flex-wrap items-center gap-1.5" data-test="rental-status-filter-bar">
    <button
      v-for="filter in filters"
      :key="filter.value"
      type="button"
      class="px-2.5 py-1 text-xs rounded-lg font-medium transition-all flex items-center gap-1.5 focus:outline-none focus:ring-1 focus:ring-cortex-primary-500"
      :class="selectedState === filter.value
        ? 'bg-cortex-primary-700 text-white shadow-xs font-semibold'
        : 'bg-cortex-surface text-cortex-text-secondary border border-cortex-border hover:bg-cortex-surface-secondary hover:text-cortex-text-primary'"
      :data-test="`filter-chip-${filter.value}`"
      @click="emit('update:selectedState', filter.value)"
    >
      <span>{{ filter.label }}</span>
      <span
        v-if="counts && counts[filter.value] !== undefined"
        class="px-1.5 py-0.2 rounded-full text-[10px] font-mono"
        :class="selectedState === filter.value ? 'bg-white/20 text-white' : 'bg-cortex-surface-secondary text-cortex-text-muted border border-cortex-border'"
      >
        {{ counts[filter.value] }}
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { RentalState } from '@/types/rental'

const { t } = useI18n()

withDefaults(
  defineProps<{
    selectedState: RentalState | 'all'
    counts?: Record<string, number>
  }>(),
  {
    selectedState: 'all'
  }
)

const emit = defineEmits<{
  (e: 'update:selectedState', val: RentalState | 'all'): void
}>()

const filters = computed<Array<{ label: string; value: RentalState | 'all' }>>(() => [
  { label: t('rentals.filter_all'), value: 'all' },
  { label: t('rental_states.Quote'), value: 'Quote' },
  { label: t('rental_states.Reservation'), value: 'Reservation' },
  { label: t('rental_states.Contract'), value: 'Contract' },
  { label: t('rental_states.Checked Out'), value: 'Checked Out' },
  { label: t('rental_states.Partially Returned'), value: 'Partially Returned' },
  { label: t('rental_states.Returned'), value: 'Returned' },
  { label: t('rental_states.Invoiced'), value: 'Invoiced' },
  { label: t('rental_states.Cancelled'), value: 'Cancelled' }
])
</script>
