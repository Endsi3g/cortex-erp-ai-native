<template>
  <div data-test="tab-audit-log">
    <div class="flex items-center justify-between gap-3">
      <h3 class="m-0 text-base font-semibold">Journal d'audit (ajout seulement)</h3>
      <span class="text-sm" style="color: var(--erp-muted)">{{ auditEvents.length }} événement(s)</span>
    </div>
    <p v-if="isLoading" class="cx-empty">Chargement des traces d'audit…</p>
    <p v-else-if="auditEvents.length === 0" class="cx-empty"><strong>Aucun événement</strong>Aucun événement d'audit disponible pour cette transaction.</p>
    <div v-else class="cx-tablewrap mt-3">
      <table class="cx-table">
        <thead><tr><th scope="col" class="cx-rownum">#</th><th scope="col">Date</th><th scope="col">Action</th><th scope="col">Acteur</th><th scope="col">Détail</th></tr></thead>
        <tbody>
          <tr v-for="(event, index) in auditEvents" :key="event.id" :data-test="`audit-event-${event.id}`">
            <td class="cx-rownum">{{ index + 1 }}</td>
            <td>{{ formatDate(event.timestamp) }}</td>
            <td>{{ formatAuditActionTitle(event.action) }}</td>
            <td>{{ event.actor.actor_type }}: <span class="font-mono">{{ event.actor.actor_id }}</span></td>
            <td class="wrap font-mono text-xs">{{ event.diff_summary || '—' }}</td>
          </tr>
        </tbody>
      </table>
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
