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
      <select
        :value="category"
        class="text-xs px-2.5 py-1.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:outline-none focus:ring-1 focus:ring-cortex-primary-500"
        data-test="category-filter"
        @change="emit('update:category', ($event.target as HTMLSelectElement).value)"
      >
        <option value="all">Toutes les catégories</option>
        <option value="Cameras">Caméras</option>
        <option value="Lenses">Optiques</option>
        <option value="Lighting">Éclairage</option>
        <option value="Grip">Machinerie & Grip</option>
        <option value="Audio">Son & HF</option>
        <option value="Monitoring">Monitoring</option>
        <option value="Power & Batteries">Énergie</option>
      </select>

      <!-- Search Input -->
      <div class="relative min-w-[180px]">
        <input
          type="text"
          :value="search"
          placeholder="Filtrer équipement..."
          class="w-full text-xs pl-7 pr-2.5 py-1.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary placeholder:text-cortex-text-muted focus:outline-none focus:ring-1 focus:ring-cortex-primary-500"
          data-test="equipment-search-input"
          @input="emit('update:search', ($event.target as HTMLInputElement).value)"
        />
        <Search class="w-3.5 h-3.5 absolute left-2 top-2 text-cortex-text-muted pointer-events-none" />
      </div>
    </div>

    <!-- Right: Date Navigation & Create Quote CTA -->
    <div class="flex items-center gap-2 justify-between lg:justify-end">
      <!-- Date Navigation -->
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="p-1 rounded-md border border-cortex-border hover:bg-cortex-surface-secondary text-cortex-text-muted hover:text-cortex-text-primary"
          title="Précédent"
          @click="emit('navigate', 'prev')"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>
        <button
          type="button"
          class="px-2.5 py-1 text-xs rounded-md border border-cortex-border font-medium hover:bg-cortex-surface-secondary text-cortex-text-primary"
          @click="emit('navigate', 'today')"
        >
          Aujourd'hui
        </button>
        <button
          type="button"
          class="p-1 rounded-md border border-cortex-border hover:bg-cortex-surface-secondary text-cortex-text-muted hover:text-cortex-text-primary"
          title="Suivant"
          @click="emit('navigate', 'next')"
        >
          <ChevronRight class="w-4 h-4" />
        </button>
        <span class="text-xs font-semibold text-cortex-text-primary ml-1.5">
          {{ dateLabel }}
        </span>
      </div>

      <!-- Create Quote Button (Flow 2) -->
      <button
        type="button"
        class="cx-btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5 whitespace-nowrap"
        :disabled="selectedEquipmentCodes.length === 0"
        data-test="create-quote-btn"
        @click="emit('create-quote')"
      >
        <PlusCircle class="w-3.5 h-3.5" />
        <span>{{ t('availability.create_quote') }}</span>
        <span
          v-if="selectedEquipmentCodes.length > 0"
          class="px-1.5 py-0.2 rounded-full bg-white/20 text-[10px] font-bold"
          data-test="selected-count-badge"
        >
          {{ selectedEquipmentCodes.length }}
        </span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Search, ChevronLeft, ChevronRight, PlusCircle } from 'lucide-vue-next'

const { t } = useI18n()

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
