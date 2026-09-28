<template>
  <div class="cx-page" data-test="screen-consignment-dashboard">
    <CortexPageHeader title="Consignation" subtitle="Versements dus aux propriétaires tiers, calculés depuis les versements enregistrés." :provenance="dashboard?.provenance">
      <template #actions>
        <RouterLink to="/app/cortex-consignment-owner" class="cx-btn-soft">Propriétaires</RouterLink>
        <RefreshButton :loading="isLoading" @refresh="loadDashboard" />
      </template>
    </CortexPageHeader>

    <div class="cx-filters">
      <FilterField label="Période">
        <select id="period-select" v-model="selectedPeriod" class="cx-field" @change="loadDashboard">
          <option v-for="option in periodOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </FilterField>
    </div>

    <div v-if="errorMessage" class="cx-section"><CortexErrorBanner :error-message="errorMessage" @retry="loadDashboard" /></div>
    <div v-if="isLoading && !dashboard" class="cx-section"><CortexSkeleton variant="table-row" :count="4" /></div>

    <template v-if="dashboard">
      <KpiStrip :items="kpis" />

      <section class="cx-section" aria-labelledby="stmt-title">
        <h2 id="stmt-title">Relevés en attente</h2>
        <div v-if="!dashboard.pending_statements.length" class="cx-empty"><strong>Aucun relevé en attente</strong>Tous les versements de la période sont réglés ou n'existent pas encore.</div>
        <div v-else class="cx-tablewrap">
          <table class="cx-table">
            <thead><tr><th scope="col" class="cx-rownum">#</th><th scope="col">Propriétaire</th><th scope="col">Période</th><th scope="col">Statut</th><th scope="col" class="num">Montant dû</th><th scope="col"><span class="sr-only">Relevé</span></th></tr></thead>
            <tbody>
              <tr v-for="(stmt, index) in dashboard.pending_statements" :key="`${stmt.owner_id}:${stmt.period}`">
                <td class="cx-rownum">{{ index + 1 }}</td>
                <td>{{ stmt.owner_name }}</td>
                <td class="num">{{ stmt.period }}</td>
                <td>{{ STATUS_LABELS[stmt.status] }}</td>
                <td class="num">{{ formatCurrency(stmt.amount_due) }}</td>
                <td><RouterLink :to="`/app/cortex-owner-statement/${encodeURIComponent(stmt.owner_id)}/${stmt.period}`" :data-test="`view-statement-${stmt.owner_id}`">Consulter le relevé</RouterLink></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="cx-section" aria-labelledby="top-title">
        <h2 id="top-title">Équipements les plus rentables</h2>
        <div v-if="!dashboard.top_earning_items.length" class="cx-empty"><strong>Aucun revenu de consignation</strong>Aucun versement n'est enregistré pour cette période.</div>
        <div v-else class="cx-tablewrap">
          <table class="cx-table">
            <thead><tr><th scope="col" class="cx-rownum">#</th><th scope="col">Équipement</th><th scope="col">Propriétaire</th><th scope="col" class="num">Revenu net</th><th scope="col" class="num">Versement propriétaire</th></tr></thead>
            <tbody>
              <tr v-for="(item, index) in dashboard.top_earning_items" :key="item.item_code">
                <td class="cx-rownum">{{ index + 1 }}</td>
                <td>{{ item.item_name }}<div class="font-mono text-xs" style="color: var(--erp-muted)">{{ item.item_code }}</div></td>
                <td class="font-mono">{{ item.owner_code }}</td>
                <td class="num">{{ formatCurrency(item.revenue_generated) }}</td>
                <td class="num">{{ formatCurrency(item.owner_payout) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getCortexApiClient } from '@/api'
import type { ConsignmentDashboardResponse } from '@/api/contracts'
import { formatCurrency } from '@/utils/formatters'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import FilterField from '@/features/common/components/FilterField.vue'
import KpiStrip, { type KpiItem } from '@/features/common/components/KpiStrip.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'

const STATUS_LABELS: Record<string, string> = { draft: 'Calculé', approved: 'Approuvé', paid: 'Payé' }

// Last six months, current month first (the server default period is the current month).
const periodOptions = Array.from({ length: 6 }, (_, back) => {
  const date = new Date()
  date.setDate(1)
  date.setMonth(date.getMonth() - back)
  const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
  return { value, label: date.toLocaleDateString('fr-CA', { month: 'long', year: 'numeric' }) }
})

const selectedPeriod = ref(periodOptions[0].value)
const dashboard = ref<ConsignmentDashboardResponse | null>(null)
const isLoading = ref(true)
const errorMessage = ref('')

const kpis = computed<KpiItem[]>(() => dashboard.value ? [
  { key: 'current', label: 'Versements du mois', value: formatCurrency(dashboard.value.current_month_total_payout), positive: true },
  { key: 'previous', label: 'Mois précédent', value: formatCurrency(dashboard.value.previous_month_total_payout) },
  { key: 'owners', label: 'Propriétaires', value: String(dashboard.value.active_owners_count) },
  { key: 'serials', label: 'Séries en consignation', value: String(dashboard.value.active_consigned_serials_count) }
] : [])

async function loadDashboard() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    dashboard.value = await getCortexApiClient().getConsignmentDashboard({ period: selectedPeriod.value })
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors du chargement de la consignation.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadDashboard)
</script>
