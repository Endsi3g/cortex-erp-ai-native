<template>
  <div class="cx-page" data-test="screen-operations-overview">
    <CortexPageHeader title="Opérations" subtitle="Départs, retours et exceptions du jour, calculés depuis les transactions." :provenance="data?.provenance">
      <template #actions>
        <RefreshButton :loading="loading" @refresh="reload" />
        <RouterLink to="/app/cortex-rental/new" class="cx-btn-primary">Nouveau devis</RouterLink>
      </template>
    </CortexPageHeader>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>

    <KpiStrip :items="kpis" @select="toggleFilter" />

    <div class="cx-two">
      <section class="cx-section" aria-labelledby="ops-timeline">
        <h2 id="ops-timeline">Chronologie du jour</h2>
        <CortexSkeleton v-if="loading && !data" variant="table-row" :count="4" />
        <div v-else-if="!visibleTimeline.length" class="cx-empty">
          <strong>Aucun mouvement prévu</strong>
          Aucun départ ni retour n'est planifié aujourd'hui pour cette entreprise.
          <div class="mt-4"><RouterLink to="/app/cortex-availability" class="cx-btn-soft">Ouvrir la disponibilité</RouterLink></div>
        </div>
        <div v-else class="cx-tablewrap">
          <table class="cx-table">
            <thead>
              <tr>
                <th scope="col" class="cx-rownum">#</th>
                <th scope="col">Heure</th>
                <th scope="col">Mouvement</th>
                <th scope="col">Location</th>
                <th scope="col">Client</th>
                <th scope="col">État</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(entry, index) in visibleTimeline" :key="`${entry.kind}:${entry.rental_id}`">
                <td class="cx-rownum">{{ index + 1 }}</td>
                <td class="num">{{ time(entry.at) }}</td>
                <td>{{ entry.kind === 'departure' ? 'Départ' : 'Retour' }}</td>
                <td><RouterLink :to="`/app/cortex-rental/${entry.rental_id}`">{{ entry.rental_id }}</RouterLink></td>
                <td class="truncate-cell" :title="entry.customer">{{ entry.customer }}</td>
                <td>{{ stateLabel(entry.state) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="cx-section" aria-labelledby="ops-attention">
        <h2 id="ops-attention">À traiter</h2>
        <ul v-if="attention.length" class="cx-list">
          <li v-for="item in attention" :key="item.key">
            <RouterLink :to="item.to"><span>{{ item.label }}</span><strong class="tabular-nums">{{ item.count }}</strong></RouterLink>
          </li>
        </ul>
        <p v-else-if="data" class="text-sm" style="color: var(--erp-muted)">Rien à traiter pour le moment.</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getCortexApiClient } from '@/api'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import KpiStrip, { type KpiItem } from '@/features/common/components/KpiStrip.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

type Filter = 'all' | 'departure' | 'return'

const { data, loading, error, reload } = useResource(() => getCortexApiClient().getOperationsOverview())
const activeFilter = ref<Filter>('all')

const STATE_LABELS: Record<string, string> = {
  Quote: 'Soumission', Reservation: 'Réservation', Contract: 'Contrat', 'Checked Out': 'Sortie',
  Returned: 'Retourné', Closed: 'Clôturé', Cancelled: 'Annulé', Disputed: 'Contesté', Quarantine: 'Quarantaine'
}
const stateLabel = (state: string): string => STATE_LABELS[state] ?? state
const time = (at: string): string => (at.length >= 16 ? at.slice(11, 16) : at)
const show = (value: number | null | undefined): string => (loading.value && !data.value ? '…' : value == null ? '—' : String(value))

const kpis = computed<KpiItem[]>(() => {
  const counts = data.value?.counts
  return [
    { key: 'departure', label: 'Départs aujourd’hui', value: show(counts?.departures_today), selectable: true, pressed: activeFilter.value === 'departure' },
    {
      key: 'return', label: 'Retours attendus', value: show(counts?.returns_due_today), selectable: true, pressed: activeFilter.value === 'return',
      detail: counts && counts.overdue_returns > 0 ? `dont ${counts.overdue_returns} en retard` : undefined
    },
    { key: 'exceptions', label: 'Exceptions', value: show(counts?.exceptions), to: '/app/cortex-rentals?state=Disputed' },
    {
      key: 'approvals', label: 'Approbations en attente', value: show(counts?.pending_approvals),
      to: counts?.pending_approvals == null ? undefined : '/app/cortex-ai-inbox?type=approval', hint: 'Réservé aux rôles qui peuvent décider une approbation.'
    }
  ]
})

const attention = computed(() => {
  const counts = data.value?.counts
  if (!counts) return []
  return [
    { key: 'overdue', label: 'Retours en retard', count: counts.overdue_returns, to: '/app/cortex-rentals?state=Checked Out' },
    { key: 'disputed', label: 'Locations contestées ou en quarantaine', count: counts.disputed_or_quarantined, to: '/app/cortex-rentals?state=Disputed' },
    { key: 'missing', label: 'Numéros de série manquants', count: counts.missing_serials, to: '/app/cortex-equipment' },
    { key: 'inbound', label: 'Demandes entrantes à réviser', count: counts.inbound_to_review, to: '/app/cortex-ai-inbox?type=inbound' }
  ].filter((item) => item.count > 0)
})

const visibleTimeline = computed(() => (data.value?.timeline ?? []).filter((entry) => activeFilter.value === 'all' || entry.kind === activeFilter.value))
const toggleFilter = (key: string): void => {
  const filter = key as Filter
  activeFilter.value = activeFilter.value === filter ? 'all' : filter
}
</script>
