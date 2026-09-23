<template>
  <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 p-3 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs" data-test="availability-toolbar">
    <!-- Left: Granularity & Category -->
    <div class="flex flex-wrap items-center gap-2.5">
      <!-- Granularity Toggle -->
      <div class="inline-flex rounded-lg border border-cortex-border bg-cortex-surface-secondary p-0.5" role="group" data-test="granularity-toggle">
        <button
          type="button"
          class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
          :class="granularity === 'day' ? 'bg-cortex-surface text-cortex-text-primary shadow-xs font-semibold' : 'text-cortex-text-muted hover:text-cortex-text-primary'"
          data-test="granularity-day-btn"
          @click="emit('update:granularity', 'day')"
        >
          {{ t('availability.granularity_day') }}
        </button>
        <button
          type="button"
          class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
          :class="granularity === 'week' ? 'bg-cortex-surface text-cortex-text-primary shadow-xs font-semibold' : 'text-cortex-text-muted hover:text-cortex-text-primary'"
          data-test="granularity-week-btn"
          @click="emit('update:granularity', 'week')"
        >
          {{ t('availability.granularity_week') }}
        </button>
        <button
          type="button"
          class="px-3 py-1 text-xs font-medium rounded-md transition-colors"
          :class="granularity === 'month' ? 'bg-cortex-surface text-cortex-text-primary shadow-xs font-semibold' : 'text-cortex-text-muted hover:text-cortex-text-primary'"
          data-test="granularity-month-btn"
          @click="emit('update:granularity', 'month')"
        >
          {{ t('availability.granularity_month') }}
        </button>
      </div>

      <!-- Category Filter -->
      <Select
        :model-value="category"
        class="min-w-40"
        size="sm"
        variant="outline"
        data-test="category-filter"
        aria-label="Filtrer par catégorie"
        :options="categoryOptions"
        @update:model-value="emit('update:category', String($event || 'all'))"
      />

      <!-- Search Input -->
      <div class="min-w-[180px]">
        <TextInput
          :model-value="search"
          type="search"
          size="sm"
          variant="outline"
          placeholder="Filtrer équipement..."
          aria-label="Rechercher un équipement"
          data-test="equipment-search-input"
          @update:model-value="emit('update:search', $event)"
        />
      </div>
    </div>

    <!-- Right: Date Navigation & Create Quote CTA -->
    <div class="flex items-center gap-2 justify-between lg:justify-end">
      <!-- Date Navigation -->
      <div class="flex items-center gap-1">
        <Button size="sm" variant="outline" icon="chevron-left" aria-label="Période précédente" @click="emit('navigate', 'prev')" />
        <Button size="sm" variant="outline" @click="emit('navigate', 'today')">Aujourd’hui</Button>
        <Button size="sm" variant="outline" icon="chevron-right" aria-label="Période suivante" @click="emit('navigate', 'next')" />
        <span class="text-xs font-semibold text-cortex-text-primary ml-1.5">
          {{ dateLabel }}
        </span>
      </div>

      <!-- Create Quote Button (Flow 2) -->
      <Button
        type="button"
        size="sm"
        theme="green"
        variant="solid"
        :disabled="selectedEquipmentCodes.length === 0"
        data-test="create-quote-btn"
        @click="emit('create-quote')"
      >
        {{ t('availability.create_quote') }}<Badge v-if="selectedEquipmentCodes.length > 0" class="ml-1" theme="green" variant="subtle" data-test="selected-count-badge">{{ selectedEquipmentCodes.length }}</Badge>
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Badge, Button, Select, TextInput } from 'frappe-ui'

const { t } = useI18n()
const categoryOptions = [
  { label: 'Toutes les catégories', value: 'all' }, { label: 'Caméras', value: 'Cameras' },
  { label: 'Optiques', value: 'Lenses' }, { label: 'Éclairage', value: 'Lighting' },
  { label: 'Machinerie & Grip', value: 'Grip' }, { label: 'Son & HF', value: 'Audio' },
  { label: 'Monitoring', value: 'Monitoring' }, { label: 'Énergie', value: 'Power & Batteries' }
]

withDefaults(
  defineProps<{
    granularity: 'day' | 'week' | 'month'
    category: string
    search: string
    dateLabel: string
    selectedEquipmentCodes: string[]
  }>(),
  {
    granularity: 'week',
    category: 'all',
    search: '',
    dateLabel: 'Septembre 2026',
    selectedEquipmentCodes: () => []
  }
)

const emit = defineEmits<{
  (e: 'update:granularity', val: 'day' | 'week' | 'month'): void
  (e: 'update:category', val: string): void
  (e: 'update:search', val: string): void
  (e: 'navigate', direction: 'prev' | 'next' | 'today'): void
  (e: 'create-quote'): void
}>()
</script>
