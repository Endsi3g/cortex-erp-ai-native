<template>
  <label class="block" data-test="rental-status-filter-bar">
    <span class="sr-only">Statut</span>
    <select class="cx-field" :value="selectedState" @change="emit('update:selectedState', ($event.target as HTMLSelectElement).value as RentalState | 'all')">
      <option v-for="filter in filters" :key="filter.value" :value="filter.value">
        {{ filter.value === 'all' ? 'Statut' : filter.label }}{{ counts && counts[filter.value] !== undefined ? ` (${counts[filter.value]})` : '' }}
      </option>
    </select>
  </label>
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

// Values the backend can store in Cortex Rental Transaction.rental_state (no invented states).
const filters = computed<Array<{ label: string; value: RentalState | 'all' }>>(() => [
  { label: t('rentals.filter_all'), value: 'all' },
  { label: t('rental_states.Quote'), value: 'Quote' },
  { label: t('rental_states.Reservation'), value: 'Reservation' },
  { label: t('rental_states.Contract'), value: 'Contract' },
  { label: t('rental_states.Checked Out'), value: 'Checked Out' },
  { label: t('rental_states.Returned'), value: 'Returned' },
  { label: t('rental_states.Cancelled'), value: 'Cancelled' }
])
</script>
