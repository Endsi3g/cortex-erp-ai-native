<template>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4" data-test="operations-kpi-cards">
    <!-- 1. Départs -->
    <div
      class="p-4 rounded-xl border bg-cortex-surface shadow-2xs cursor-pointer transition-all hover:border-cortex-primary-400 focus:outline-none focus:ring-2 focus:ring-cortex-primary-400"
      :class="activeFilter === 'departures' ? 'border-cortex-primary-500 ring-2 ring-cortex-primary-200 bg-cortex-primary-50/20' : 'border-cortex-border'"
      tabindex="0"
      role="button"
      :aria-pressed="activeFilter === 'departures'"
      @click="toggleFilter('departures')"
      @keydown.enter="toggleFilter('departures')"
      @keydown.space.prevent="toggleFilter('departures')"
    >
      <div class="flex items-center justify-between">
        <span class="text-xs text-cortex-text-muted font-medium">{{ t('operations.kpi_departures') }}</span>
        <LogOut class="w-4 h-4 text-cortex-primary-600" />
      </div>
      <div class="mt-2 flex items-baseline gap-2">
        <span class="text-2xl font-bold font-mono text-cortex-text-primary">{{ departuresCount }}</span>
        <span class="text-[11px] text-cortex-primary-700 font-medium">4 prêts</span>
      </div>
      <div class="mt-2 text-[11px] text-cortex-text-muted flex items-center justify-between">
        <span>Aujourd'hui</span>
        <span class="font-medium text-cortex-primary-600">{{ activeFilter === 'departures' ? '● Actif' : 'Filtrer' }}</span>
      </div>
    </div>

    <!-- 2. Retours -->
    <div
      class="p-4 rounded-xl border bg-cortex-surface shadow-2xs cursor-pointer transition-all hover:border-cortex-primary-400 focus:outline-none focus:ring-2 focus:ring-cortex-primary-400"
      :class="activeFilter === 'returns' ? 'border-amber-500 ring-2 ring-amber-200 bg-amber-50/20' : 'border-cortex-border'"
      tabindex="0"
      role="button"
      :aria-pressed="activeFilter === 'returns'"
      @click="toggleFilter('returns')"
      @keydown.enter="toggleFilter('returns')"
      @keydown.space.prevent="toggleFilter('returns')"
    >
      <div class="flex items-center justify-between">
        <span class="text-xs text-cortex-text-muted font-medium">{{ t('operations.kpi_returns') }}</span>
        <LogIn class="w-4 h-4 text-amber-600" />
      </div>
      <div class="mt-2 flex items-baseline gap-2">
        <span class="text-2xl font-bold font-mono text-cortex-text-primary">{{ returnsCount }}</span>
        <span class="text-[11px] text-amber-700 font-medium">2 en retard</span>
      </div>
      <div class="mt-2 text-[11px] text-cortex-text-muted flex items-center justify-between">
        <span>Attendus</span>
        <span class="font-medium text-amber-600">{{ activeFilter === 'returns' ? '● Actif' : 'Filtrer' }}</span>
      </div>
    </div>

    <!-- 3. Exceptions & Bris -->
    <div
      class="p-4 rounded-xl border bg-cortex-surface shadow-2xs cursor-pointer transition-all hover:border-red-400 focus:outline-none focus:ring-2 focus:ring-red-400"
      :class="activeFilter === 'exceptions' ? 'border-red-500 ring-2 ring-red-200 bg-red-50/20' : 'border-cortex-border'"
      tabindex="0"
      role="button"
      :aria-pressed="activeFilter === 'exceptions'"
      @click="toggleFilter('exceptions')"
      @keydown.enter="toggleFilter('exceptions')"
      @keydown.space.prevent="toggleFilter('exceptions')"
    >
      <div class="flex items-center justify-between">
        <span class="text-xs text-cortex-text-muted font-medium">{{ t('operations.kpi_exceptions') }}</span>
        <AlertTriangle class="w-4 h-4 text-red-600" />
      </div>
      <div class="mt-2 flex items-baseline gap-2">
        <span class="text-2xl font-bold font-mono text-red-600">{{ exceptionsCount }}</span>
        <span class="text-[11px] text-red-700 font-medium">1 quarantaine</span>
      </div>
      <div class="mt-2 text-[11px] text-cortex-text-muted flex items-center justify-between">
        <span>Anomalies</span>
        <span class="font-medium text-red-600">{{ activeFilter === 'exceptions' ? '● Actif' : 'Filtrer' }}</span>
      </div>
    </div>

    <!-- 4. Approbations SAS -->
    <div
      class="p-4 rounded-xl border bg-cortex-surface shadow-2xs cursor-pointer transition-all hover:border-cortex-primary-400 focus:outline-none focus:ring-2 focus:ring-cortex-primary-400"
      :class="activeFilter === 'approvals' ? 'border-cortex-primary-500 ring-2 ring-cortex-primary-200 bg-cortex-primary-50/20' : 'border-cortex-border'"
      tabindex="0"
      role="button"
      :aria-pressed="activeFilter === 'approvals'"
      @click="toggleFilter('approvals')"
      @keydown.enter="toggleFilter('approvals')"
      @keydown.space.prevent="toggleFilter('approvals')"
    >
      <div class="flex items-center justify-between">
        <span class="text-xs text-cortex-text-muted font-medium">{{ t('operations.kpi_approvals') }}</span>
        <ShieldCheck class="w-4 h-4 text-amber-600" />
      </div>
      <div class="mt-2 flex items-baseline gap-2">
        <span class="text-2xl font-bold font-mono text-amber-600">{{ approvalsCount }}</span>
        <span class="text-[11px] text-amber-700 font-medium">Action requise</span>
      </div>
      <div class="mt-2 text-[11px] text-cortex-text-muted flex items-center justify-between">
        <span>File SAS</span>
        <span class="font-medium text-amber-600">{{ activeFilter === 'approvals' ? '● Actif' : 'Filtrer' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { LogOut, LogIn, AlertTriangle, ShieldCheck } from 'lucide-vue-next'

const { t } = useI18n()

export type OperationsFilter = 'all' | 'departures' | 'returns' | 'exceptions' | 'approvals'

const props = withDefaults(
  defineProps<{
    activeFilter?: OperationsFilter
    departuresCount?: number
    returnsCount?: number
    exceptionsCount?: number
    approvalsCount?: number
  }>(),
  {
    activeFilter: 'all',
    departuresCount: 8,
    returnsCount: 11,
    exceptionsCount: 3,
    approvalsCount: 4
  }
)

const emit = defineEmits<{
  (e: 'update:activeFilter', value: OperationsFilter): void
}>()

const toggleFilter = (filter: OperationsFilter) => {
  if (props.activeFilter === filter) {
    emit('update:activeFilter', 'all')
  } else {
    emit('update:activeFilter', filter)
  }
}
</script>
