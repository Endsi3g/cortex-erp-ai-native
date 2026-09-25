<template>
  <div class="rounded-xl border border-cortex-border bg-cortex-surface p-5 shadow-2xs" data-test="operations-timeline">
    <div class="flex items-center justify-between pb-4 border-b border-cortex-border">
      <div class="flex items-center gap-2">
        <Clock class="w-5 h-5 text-cortex-primary-600" />
        <h2 class="text-base font-semibold text-cortex-text-primary">{{ t('operations.timeline_title') }}</h2>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs text-cortex-text-muted font-medium">8 septembre 2026</span>
        <span
          v-if="activeFilter !== 'all'"
          class="px-2 py-0.5 text-xs rounded-full bg-cortex-primary-100 text-cortex-primary-800 font-medium"
        >
          Filtre: {{ activeFilterLabel }}
        </span>
      </div>
    </div>

    <!-- Timeline List -->
    <div class="mt-4 space-y-4">
      <div
        v-for="event in filteredEvents"
        :key="event.id"
        class="flex flex-col sm:flex-row items-start gap-4 p-3.5 rounded-lg border transition-all hover:bg-cortex-bg-secondary/40"
        :class="getEventBorderClass(event)"
        :data-test="`timeline-event-${event.id}`"
      >
        <!-- Time Badge -->
        <div class="flex sm:flex-col items-center gap-2 sm:gap-0 min-w-[72px]">
          <span class="text-sm font-bold font-mono text-cortex-text-primary">{{ event.time }}</span>
          <span class="text-[10px] uppercase font-semibold tracking-wider text-cortex-text-muted">{{ event.typeLabel }}</span>
        </div>

        <!-- Details -->
        <div class="flex-1 min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-mono font-semibold text-xs text-cortex-primary-700">{{ event.rentalId }}</span>
            <CortexBadge :state="event.badgeState" size="sm" />
            <span class="text-xs font-semibold text-cortex-text-primary truncate">{{ event.customerName }}</span>
            <span v-if="event.projectName" class="text-xs text-cortex-text-muted truncate">({{ event.projectName }})</span>
          </div>

          <p class="mt-1 text-xs text-cortex-text-secondary">{{ event.description }}</p>

          <div class="mt-2 flex flex-wrap items-center gap-1.5">
            <span
              v-for="item in event.equipmentItems"
              :key="item"
              class="px-2 py-0.5 rounded bg-cortex-surface-secondary text-[11px] text-cortex-text-secondary font-mono border border-cortex-border"
            >
              {{ item }}
            </span>
          </div>
        </div>

        <!-- Action Button -->
        <div class="w-full sm:w-auto flex items-center justify-end">
          <RouterLink
            :to="event.actionLink"
            class="cx-btn-secondary text-xs px-3 py-1.5 whitespace-nowrap"
            :data-test="`timeline-action-${event.id}`"
          >
            {{ event.actionLabel }}
          </RouterLink>
        </div>
      </div>

      <div v-if="filteredEvents.length === 0" class="py-8 text-center text-cortex-text-muted text-xs">
        Aucun événement correspondant au filtre actif.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Clock } from 'lucide-vue-next'
import CortexBadge from '@/design-system/components/base/CortexBadge.vue'
import type { OperationsFilter } from './OperationsKpiCards.vue'

const { t } = useI18n()

interface TimelineEvent {
  id: string
  time: string
  type: 'departure' | 'return' | 'exception' | 'approval'
  typeLabel: string
  rentalId: string
  customerName: string
  projectName?: string
  badgeState: 'quote' | 'reservation' | 'contract' | 'checked_out' | 'partial_return' | 'returned' | 'invoiced'
  description: string
  equipmentItems: string[]
  actionLabel: string
  actionLink: string
}

const props = withDefaults(
  defineProps<{
    activeFilter?: OperationsFilter
  }>(),
  {
    activeFilter: 'all'
  }
)

const events: TimelineEvent[] = [
  {
    id: 'evt-1',
    time: '08:00',
    type: 'departure',
    typeLabel: 'Départ',
    rentalId: 'DEMO-TRX-2026-006',
    customerName: 'Production Nord Inc.',
    projectName: 'Commercial Campaign — Horizon 2026',
    badgeState: 'contract',
    description: 'Sortie d’équipement confirmée. Prêt pour scan en entrepôt.',
    equipmentItems: ['ARRI Alexa 35 (#DEMO-SN-ALX-002)', 'Cooke S4/i Set (#DEMO-SN-CKE-102)'],
    actionLabel: 'Sortie (Check-out)',
    actionLink: '/checkout/DEMO-TRX-2026-006'
  },
  {
    id: 'evt-2',
    time: '10:30',
    type: 'departure',
    typeLabel: 'Départ',
    rentalId: 'DEMO-TRX-2026-001',
    customerName: 'Production Nord Inc.',
    projectName: 'Feature Film — Laurentian Winter',
    badgeState: 'checked_out',
    description: 'Enlèvement par Marc-André (DP). Matériel actuellement hors-location.',
    equipmentItems: ['ARRI Alexa 35 (#DEMO-SN-ALX-001)', 'Cooke S4/i (#DEMO-SN-CKE-101)'],
    actionLabel: 'Voir 360°',
    actionLink: '/rentals/DEMO-TRX-2026-001'
  },
  {
    id: 'evt-3',
    time: '14:00',
    type: 'return',
    typeLabel: 'Retour',
    rentalId: 'DEMO-TRX-2026-004',
    customerName: 'Production Nord Inc.',
    projectName: 'Commercial Teaser',
    badgeState: 'partial_return',
    description: 'Retour partiel reçu. Anomalie : adaptateur optique manquant.',
    equipmentItems: ['ARRI Alexa 35 (#DEMO-SN-ALX-004)', 'Adaptateur PL/LPL (Manquant)'],
    actionLabel: 'Retour (Check-in)',
    actionLink: '/checkin/DEMO-TRX-2026-004'
  },
  {
    id: 'evt-4',
    time: '17:30',
    type: 'return',
    typeLabel: 'Retour',
    rentalId: 'DEMO-TRX-2026-005',
    customerName: 'Studio Lumière Montréal',
    projectName: 'Music Video — MTL Beats',
    badgeState: 'invoiced',
    description: 'Retour complet validé et facturé sous ERPNext SINV-2026-0042.',
    equipmentItems: ['ARRI Alexa 35 (#DEMO-SN-ALX-003)'],
    actionLabel: 'Voir 360°',
    actionLink: '/rentals/DEMO-TRX-2026-005'
  }
]

const filteredEvents = computed(() => {
  if (props.activeFilter === 'all') return events
  if (props.activeFilter === 'departures') return events.filter(e => e.type === 'departure')
  if (props.activeFilter === 'returns') return events.filter(e => e.type === 'return')
  if (props.activeFilter === 'exceptions') return events.filter(e => e.id === 'evt-3')
  if (props.activeFilter === 'approvals') return events.filter(e => e.id === 'evt-1' || e.id === 'evt-3')
  return events
})

const activeFilterLabel = computed(() => {
  switch (props.activeFilter) {
    case 'departures': return t('operations.filter_departures')
    case 'returns': return t('operations.filter_returns')
    case 'exceptions': return t('operations.filter_exceptions')
    case 'approvals': return t('operations.filter_approvals')
    default: return t('operations.filter_all')
  }
})

const getEventBorderClass = (event: TimelineEvent) => {
  if (event.type === 'departure') return 'border-cortex-border hover:border-cortex-primary-300'
  if (event.type === 'return') return 'border-cortex-border hover:border-amber-300'
  return 'border-cortex-border'
}
</script>
