<template>
  <div
    v-if="block"
    class="p-4 rounded-xl border bg-cortex-surface shadow-md space-y-3 transition-all animate-in fade-in"
    :class="block.is_conflict ? 'border-red-500 ring-2 ring-red-100' : 'border-cortex-border'"
    data-test="availability-block-inspector"
  >
    <div class="flex items-center justify-between border-b border-cortex-border pb-2.5">
      <div class="flex items-center gap-2">
        <Info class="w-4 h-4 text-cortex-primary-600" />
        <h3 class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          {{ t('availability.inspector_title') }}
        </h3>
      </div>
      <button
        type="button"
        class="text-cortex-text-muted hover:text-cortex-text-primary p-0.5 rounded"
        @click="emit('close')"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Conflict Alert Banner if conflict -->
    <div
      v-if="block.is_conflict"
      class="p-2.5 rounded-lg border-2 border-red-600 bg-red-50 text-xs text-red-900 font-medium flex items-start gap-2"
      data-test="inspector-conflict-banner"
    >
      <AlertTriangle class="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
      <div>
        <strong class="font-bold block">{{ t('availability.conflict_detected') }}</strong>
        <span>{{ block.conflict_reason || 'Chevauchement temporel détecté avec une autre réservation.' }}</span>
      </div>
    </div>

    <!-- Block Metadata -->
    <div class="space-y-1.5 text-xs">
      <div class="flex items-center justify-between">
        <span class="text-cortex-text-muted">Transaction :</span>
        <span class="font-mono font-bold text-cortex-primary-700">{{ block.rental_id }}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-cortex-text-muted">Client :</span>
        <span class="font-semibold text-cortex-text-primary">{{ block.customer_name }}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-cortex-text-muted">Statut :</span>
        <span
          class="px-2 py-0.5 rounded text-[11px] font-semibold"
          :class="getStatusClass(block.state)"
        >
          {{ block.state }}
        </span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-cortex-text-muted">Début :</span>
        <span class="font-mono text-cortex-text-secondary">{{ formatDate(block.start_date) }}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-cortex-text-muted">Fin :</span>
        <span class="font-mono text-cortex-text-secondary">{{ formatDate(block.end_date) }}</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="pt-2 border-t border-cortex-border flex items-center justify-between gap-2">
      <span class="text-[11px] text-cortex-text-muted italic">
        Double-clic pour ouvrir directement
      </span>
      <RouterLink
        :to="`/rentals/${block.rental_id}`"
        class="cx-btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5"
        data-test="inspector-open-rental-btn"
      >
        <span>Voir 360°</span>
        <ExternalLink class="w-3.5 h-3.5" />
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Info, X, AlertTriangle, ExternalLink } from 'lucide-vue-next'
import type { AvailabilityBlock } from '@/api/contracts/availability'

const { t } = useI18n()

defineProps<{
  block: AvailabilityBlock | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const getStatusClass = (state: string) => {
  switch (state) {
    case 'Quote': return 'bg-gray-100 text-gray-800 border border-dashed border-gray-400'
    case 'Reservation': return 'bg-amber-100 text-amber-900 border border-amber-300'
    case 'Contract': return 'bg-blue-100 text-blue-900 border border-blue-300'
    case 'Checked Out': return 'bg-purple-100 text-purple-900 border border-purple-300'
    case 'Quarantine': return 'bg-red-100 text-red-900 border border-red-300'
    default: return 'bg-gray-100 text-gray-800'
  }
}

const formatDate = (iso: string) => {
  try {
    const d = new Date(iso)
    return d.toLocaleString('fr-CA', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}
</script>
