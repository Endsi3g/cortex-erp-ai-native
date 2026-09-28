<template>
  <div class="mx-auto max-w-7xl space-y-8" data-test="screen-operations-overview">
    <CortexPageHeader
      title="Opérations"
      subtitle="Départs, retours et exceptions du jour, calculés depuis ERPNext."
      :provenance="data?.provenance"
    >
      <template #actions>
        <RefreshButton :loading="loading" @refresh="reload" />
        <RouterLink to="/app/cortex-rental/new" class="cx-btn-primary inline-flex min-h-[40px] items-center px-4 text-sm font-medium">
          Nouveau devis
        </RouterLink>
      </template>
    </CortexPageHeader>

    <CortexErrorBanner v-if="error" :error-message="error" @retry="reload" />

    <section aria-labelledby="ops-kpis">
      <h2 id="ops-kpis" class="sr-only">Indicateurs du jour</h2>
      <dl class="grid grid-cols-2 gap-x-8 gap-y-4 lg:grid-cols-4">
        <div v-for="kpi in kpis" :key="kpi.key">
          <dt class="text-sm text-cortex-text-secondary">{{ kpi.label }}</dt>
          <dd class="mt-1">
            <button
              v-if="kpi.filter"
              type="button"
              class="min-h-[44px] text-left text-3xl font-semibold tabular-nums text-cortex-text-primary hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-cortex-primary-600"
              :aria-pressed="activeFilter === kpi.filter"
              :title="`Filtrer la chronologie: ${kpi.label}`"
              @click="toggleFilter(kpi.filter)"
            >
              {{ kpi.value }}
            </button>
            <RouterLink
              v-else-if="kpi.to && kpi.value !== '—'"
              :to="kpi.to"
              class="inline-flex min-h-[44px] items-center text-3xl font-semibold tabular-nums text-cortex-text-primary hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-cortex-primary-600"
            >
              {{ kpi.value }}
            </RouterLink>
            <span v-else class="inline-flex min-h-[44px] items-center text-3xl font-semibold tabular-nums text-cortex-text-primary" :title="kpi.hint">
              {{ kpi.value }}
            </span>
            <p v-if="kpi.detail" class="text-sm text-cortex-text-secondary">{{ kpi.detail }}</p>
          </dd>
        </div>
      </dl>
    </section>

    <div class="grid gap-8 lg:grid-cols-3">
      <section class="lg:col-span-2" aria-labelledby="ops-timeline">
        <div class="mb-2 flex items-center justify-between gap-4">
          <h2 id="ops-timeline" class="text-lg font-semibold text-cortex-text-primary">Chronologie du jour</h2>
          <button v-if="activeFilter !== 'all'" type="button" class="min-h-[44px] px-2 text-sm text-cortex-primary-700 underline" @click="activeFilter = 'all'">
            Tout afficher
          </button>
        </div>
        <CortexSkeleton v-if="loading && !data" variant="table-row" :count="4" />
        <CortexEmptyState
          v-else-if="!visibleTimeline.length"
          icon="calendar"
          title="Aucun mouvement prévu"
          description="Aucun départ ni retour n'est planifié aujourd'hui pour cette entreprise."
          action-text="Ouvrir la disponibilité"
          @action="router.push('/app/cortex-availability')"
        />
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-cortex-border text-left text-cortex-text-secondary">
                <th scope="col" class="py-2 pr-4 font-medium">Heure</th>
                <th scope="col" class="py-2 pr-4 font-medium">Mouvement</th>
                <th scope="col" class="py-2 pr-4 font-medium">Location</th>
                <th scope="col" class="py-2 pr-4 font-medium">Client</th>
                <th scope="col" class="py-2 font-medium">État</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in visibleTimeline" :key="`${entry.kind}:${entry.rental_id}`" class="min-h-[48px] border-b border-cortex-border">
                <td class="py-3 pr-4 tabular-nums">{{ time(entry.at) }}</td>
                <td class="py-3 pr-4">{{ entry.kind === 'departure' ? 'Départ' : 'Retour' }}</td>
                <td class="py-3 pr-4">
                  <RouterLink :to="`/app/cortex-rental/${entry.rental_id}`" class="font-mono text-cortex-primary-700 underline">{{ entry.rental_id }}</RouterLink>
                </td>
                <td class="max-w-[16rem] truncate py-3 pr-4" :title="entry.customer">{{ entry.customer }}</td>
                <td class="py-3">{{ stateLabel(entry.state) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="ops-attention">
        <h2 id="ops-attention" class="mb-2 text-lg font-semibold text-cortex-text-primary">À traiter</h2>
        <ul v-if="attention.length" class="divide-y divide-cortex-border border-y border-cortex-border">
          <li v-for="item in attention" :key="item.key">
            <RouterLink :to="item.to" class="flex min-h-[48px] items-center justify-between gap-4 py-2 hover:bg-cortex-surface-subtle">
              <span class="text-sm text-cortex-text-primary">{{ item.label }}</span>
              <span class="text-sm font-semibold tabular-nums text-cortex-text-primary">{{ item.count }}</span>
            </RouterLink>
          </li>
        </ul>
        <p v-else-if="data" class="text-sm text-cortex-text-secondary">Rien à traiter pour le moment.</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { getCortexApiClient } from '@/api'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexEmptyState from '@/design-system/components/states/CortexEmptyState.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

type Filter = 'all' | 'departure' | 'return'

const router = useRouter()
const { data, loading, error, reload } = useResource(() => getCortexApiClient().getOperationsOverview())
const activeFilter = ref<Filter>('all')

const STATE_LABELS: Record<string, string> = {
  Quote: 'Soumission', Reservation: 'Réservation', Contract: 'Contrat', 'Checked Out': 'Sortie',
  Returned: 'Retourné', Closed: 'Clôturé', Cancelled: 'Annulé', Disputed: 'Contesté', Quarantine: 'Quarantaine'
}
const stateLabel = (state: string): string => STATE_LABELS[state] ?? state
const time = (at: string): string => (at.length >= 16 ? at.slice(11, 16) : at)

const show = (value: number | null | undefined): string => (loading.value && !data.value ? '…' : value == null ? '—' : String(value))

const kpis = computed(() => {
  const counts = data.value?.counts
  return [
    { key: 'departures', label: 'Départs aujourd’hui', value: show(counts?.departures_today), filter: 'departure' as Filter },
    {
      key: 'returns', label: 'Retours attendus', value: show(counts?.returns_due_today), filter: 'return' as Filter,
      detail: counts && counts.overdue_returns > 0 ? `dont ${counts.overdue_returns} en retard` : undefined
    },
    { key: 'exceptions', label: 'Exceptions', value: show(counts?.exceptions), to: '/app/cortex-rentals?state=Disputed' },
    {
      key: 'approvals', label: 'Approbations en attente', value: show(counts?.pending_approvals),
      to: '/app/cortex-ai-inbox?type=approval', hint: 'Réservé aux rôles qui peuvent décider une approbation.'
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
const toggleFilter = (filter: Filter): void => { activeFilter.value = activeFilter.value === filter ? 'all' : filter }
</script>
