<template>
  <div class="space-y-4 text-xs" data-test="tab-audit-log">
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3">
      <div class="flex items-center justify-between border-b border-cortex-border pb-2.5">
        <h3 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px]">
          Journal d'Audit Immuable Append-Only
        </h3>
        <span class="font-mono text-[10px] text-cortex-text-muted">
          {{ auditEvents.length }} événements enregistrés
        </span>
      </div>

      <div v-if="isLoading" class="py-6 text-center text-cortex-text-muted">
        Chargement des traces d'audit...
      </div>

      <div v-else-if="auditEvents.length === 0" class="py-6 text-center text-cortex-text-muted">
        Aucun événement d'audit disponible pour cette transaction.
      </div>

      <div v-else class="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-cortex-border">
        <div
          v-for="event in auditEvents"
          :key="event.id"
          class="relative space-y-1"
          :data-test="`audit-event-${event.id}`"
        >
          <!-- Timeline dot -->
          <div
            class="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full border-2 bg-cortex-surface"
            :class="getActorDotClass(event.actor.actor_type)"
          />

          <div class="flex flex-wrap items-center gap-2">
            <span class="font-bold text-cortex-text-primary">
              {{ formatAuditActionTitle(event.action) }}
            </span>
            <span
              class="px-1.5 py-0.2 rounded text-[10px] font-mono font-semibold"
              :class="getActorBadgeClass(event.actor.actor_type)"
            >
              {{ event.actor.actor_type }}: {{ event.actor.actor_id }}
            </span>
            <span class="font-mono text-[10px] text-cortex-text-muted">
              {{ formatDate(event.timestamp) }}
            </span>
          </div>

          <p v-if="event.diff_summary" class="text-[11px] text-cortex-text-secondary bg-cortex-surface-secondary p-1.5 rounded border border-cortex-border font-mono">
            {{ event.diff_summary }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getCortexApiClient } from '@/api'
import { formatAuditActionTitle } from '@/utils/audit'

interface AuditEventItem {
  id: string
  timestamp: string
  actor: {
    actor_type: 'Human' | 'Agent' | 'System'
    actor_id: string
  }
  action: string
  diff_summary?: string
}

const props = defineProps<{
  rentalId: string
}>()

const isLoading = ref<boolean>(false)
const auditEvents = ref<AuditEventItem[]>([])

const loadAudit = async () => {
  isLoading.value = true
  try {
    const client = getCortexApiClient()
    const res = await client.getRentalAudit({ rental_id: props.rentalId })
    if (res && res.events) {
      auditEvents.value = res.events
    }
  } catch {
    auditEvents.value = []
  } finally {
    isLoading.value = false
  }
}

const getActorDotClass = (type: string) => {
  if (type === 'Agent') return 'border-purple-600'
  if (type === 'Human') return 'border-cortex-primary-600'
  return 'border-gray-500'
}

const getActorBadgeClass = (type: string) => {
  if (type === 'Agent') return 'bg-purple-100 text-purple-900 border border-purple-200'
  if (type === 'Human') return 'bg-cortex-primary-100 text-cortex-primary-900 border border-cortex-primary-200'
  return 'bg-gray-100 text-gray-800 border border-gray-300'
}

const formatDate = (iso: string) => {
  try {
    return new Date(iso).toLocaleString('fr-CA', { dateStyle: 'short', timeStyle: 'medium' })
  } catch {
    return iso
  }
}

onMounted(() => {
  loadAudit()
})
</script>
