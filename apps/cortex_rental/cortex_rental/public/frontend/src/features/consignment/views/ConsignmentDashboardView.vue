<template>
  <div class="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-bold text-cortex-text-primary">
            {{ $t('consignment.title', 'Consignment Dashboard — Suivi des Reversements') }}
          </h1>
          <span class="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
            F13 • PRD-CON
          </span>
        </div>
        <p class="text-xs text-cortex-text-muted mt-0.5">
          {{ $t('consignment.subtitle', 'Tableau de bord financier pour le calcul et le suivi des reversements dus aux propriétaires tiers') }}
        </p>
      </div>

      <!-- Actions / Period Switcher -->
      <div class="flex items-center gap-3">
        <label for="period-select" class="text-xs font-medium text-cortex-text-muted hidden sm:inline">
          Période :
        </label>
        <select
          id="period-select"
          v-model="selectedPeriod"
          class="px-3 py-2 text-xs font-mono font-semibold rounded-xl border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:ring-2 focus:ring-cortex-primary/30 min-h-[44px]"
          @change="loadDashboard"
        >
          <option value="2026-09">Septembre 2026 (En cours)</option>
          <option value="2026-08">Août 2026 (Clôturé)</option>
          <option value="2026-07">Juillet 2026</option>
        </select>

        <router-link
          to="/app/cortex-consignment-owner"
          class="px-4 py-2 rounded-xl border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-xs font-semibold text-cortex-text-primary transition-colors min-h-[44px] flex items-center gap-1.5"
        >
          <Users class="w-4 h-4 text-cortex-primary" />
          <span>Répertoire Propriétaires</span>
        </router-link>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="p-12 text-center text-cortex-text-muted bg-cortex-surface rounded-2xl border border-cortex-border">
      <Loader2 class="w-8 h-8 animate-spin mx-auto text-cortex-primary mb-2" />
      <span class="text-xs font-semibold">Chargement des données de consignation...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage" class="p-6 rounded-2xl border border-red-200 bg-red-50 text-red-900">
      <div class="flex items-center gap-2 font-bold text-sm">
        <AlertTriangle class="w-5 h-5 text-red-600" />
        <span>Erreur de chargement</span>
      </div>
      <p class="text-xs text-red-800 mt-1">{{ errorMessage }}</p>
    </div>

    <template v-else-if="dashboard">
      <!-- 4 KPI Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- KPI 1: Current Month Payout -->
        <div class="p-4 rounded-2xl border border-cortex-border bg-cortex-surface space-y-2">
          <div class="flex items-center justify-between text-xs text-cortex-text-muted">
            <span class="font-bold uppercase tracking-wider">Montant Dû (Mois)</span>
            <DollarSign class="w-4 h-4 text-emerald-600" />
          </div>
          <div class="text-2xl font-bold font-mono text-emerald-700">
            {{ formatMoney(dashboard.current_month_total_payout) }}
          </div>
          <div class="text-[11px] text-cortex-text-muted flex items-center gap-1">
            <span class="text-emerald-600 font-semibold">Net admissible</span>
            <span>sur la période</span>
          </div>
        </div>

        <!-- KPI 2: Previous Month Payout -->
        <div class="p-4 rounded-2xl border border-cortex-border bg-cortex-surface space-y-2">
          <div class="flex items-center justify-between text-xs text-cortex-text-muted">
            <span class="font-bold uppercase tracking-wider">Mois Précédent</span>
            <TrendingUp class="w-4 h-4 text-cortex-primary" />
          </div>
          <div class="text-2xl font-bold font-mono text-cortex-text-primary">
            {{ formatMoney(dashboard.previous_month_total_payout) }}
          </div>
          <div class="text-[11px] text-cortex-text-muted">
            Total versé aux tiers
          </div>
        </div>

        <!-- KPI 3: Active Owners Count -->
        <div class="p-4 rounded-2xl border border-cortex-border bg-cortex-surface space-y-2">
          <div class="flex items-center justify-between text-xs text-cortex-text-muted">
            <span class="font-bold uppercase tracking-wider">Propriétaires Actifs</span>
            <Users class="w-4 h-4 text-blue-600" />
          </div>
          <div class="text-2xl font-bold font-mono text-cortex-text-primary">
            {{ dashboard.active_owners_count }}
          </div>
          <div class="text-[11px] text-cortex-text-muted">
            Partenaires sous contrat
          </div>
        </div>

        <!-- KPI 4: Active Consigned Serials -->
        <div class="p-4 rounded-2xl border border-cortex-border bg-cortex-surface space-y-2">
          <div class="flex items-center justify-between text-xs text-cortex-text-muted">
            <span class="font-bold uppercase tracking-wider">Séries en Flotte</span>
            <Layers class="w-4 h-4 text-purple-600" />
          </div>
          <div class="text-2xl font-bold font-mono text-cortex-text-primary">
            {{ dashboard.active_consigned_serials_count }} unités
          </div>
          <div class="text-[11px] text-cortex-text-muted">
            Matériel tiers en exploitation
          </div>
        </div>
      </div>

      <!-- Pending Statements (Relevés en attente) — Demo Critical for Flow 4 -->
      <div class="p-5 rounded-2xl border border-cortex-border bg-cortex-surface space-y-4">
        <div class="flex items-center justify-between border-b border-cortex-border pb-3">
          <div>
            <h2 class="text-sm font-bold text-cortex-text-primary uppercase tracking-wider">
              Relevés Propriétaires en Attente ({{ dashboard.pending_statements.length }})
            </h2>
            <p class="text-xs text-cortex-text-muted mt-0.5">
              Relevés mensuels certifiés conformes au protocole d'isolation étanche OwnerStatementSafe
            </p>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-cortex-border text-cortex-text-muted font-bold uppercase tracking-wider">
                <th class="py-2.5 px-3">Propriétaire Partenaire</th>
                <th class="py-2.5 px-3">Période</th>
                <th class="py-2.5 px-3 text-right">Montant Dû</th>
                <th class="py-2.5 px-3 text-center">Statut Relevé</th>
                <th class="py-2.5 px-3 text-right">Action Étanche</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-cortex-border">
              <tr
                v-for="stmt in dashboard.pending_statements"
                :key="`${stmt.owner_id}_${stmt.period}`"
                class="hover:bg-cortex-surface-muted/40 transition-colors"
              >
                <td class="py-3 px-3 font-semibold text-cortex-text-primary">
                  {{ stmt.owner_name }}
                  <span class="block text-[11px] font-mono text-cortex-text-muted font-normal">{{ stmt.owner_id }}</span>
                </td>
                <td class="py-3 px-3 font-mono font-medium text-cortex-text-secondary">
                  {{ stmt.period }}
                </td>
                <td class="py-3 px-3 font-mono font-bold text-right text-emerald-700 text-sm">
                  {{ formatMoney(stmt.amount_due) }}
                </td>
                <td class="py-3 px-3 text-center">
                  <span
                    class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                    :class="
                      stmt.status === 'approved'
                        ? 'bg-emerald-100 text-emerald-800'
                        : stmt.status === 'paid'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-amber-100 text-amber-800'
                    "
                  >
                    {{ stmt.status === 'approved' ? 'Approuvé' : stmt.status === 'paid' ? 'Payé' : 'Brouillon' }}
                  </span>
                </td>
                <td class="py-3 px-3 text-right">
                  <router-link
                    :to="`/app/cortex-owner-statement/${stmt.owner_id}/${stmt.period}`"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cortex-primary hover:bg-cortex-primary-hover text-white text-xs font-bold transition-colors min-h-[38px] shadow-xs"
                    :data-test="`view-statement-${stmt.owner_id}`"
                  >
                    <FileCheck class="w-3.5 h-3.5" />
                    <span>Consulter le relevé étanche</span>
                    <ArrowRight class="w-3.5 h-3.5" />
                  </router-link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Top Earning Consigned Items -->
      <div class="p-5 rounded-2xl border border-cortex-border bg-cortex-surface space-y-4">
        <div class="flex items-center justify-between border-b border-cortex-border pb-3">
          <div>
            <h2 class="text-sm font-bold text-cortex-text-primary uppercase tracking-wider">
              Top Équipements Générateurs de Revenus
            </h2>
            <p class="text-xs text-cortex-text-muted mt-0.5">
              Performances locatives ventilées entre part distributeur et part propriétaire
            </p>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-cortex-border text-cortex-text-muted font-bold uppercase tracking-wider">
                <th class="py-2.5 px-3">Équipement</th>
                <th class="py-2.5 px-3">Code Propriétaire</th>
                <th class="py-2.5 px-3 text-right">Revenu Brut Généré</th>
                <th class="py-2.5 px-3 text-right">Reversement Propriétaire</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-cortex-border">
              <tr
                v-for="item in dashboard.top_earning_items"
                :key="item.item_code"
                class="hover:bg-cortex-surface-muted/40 transition-colors"
              >
                <td class="py-3 px-3 font-semibold text-cortex-text-primary">
                  {{ item.item_name }}
                  <span class="block text-[11px] font-mono text-cortex-text-muted font-normal">{{ item.item_code }}</span>
                </td>
                <td class="py-3 px-3">
                  <span class="px-2 py-0.5 rounded font-mono text-xs font-bold bg-cortex-surface-muted border border-cortex-border">
                    {{ item.owner_code }}
                  </span>
                </td>
                <td class="py-3 px-3 font-mono text-right text-cortex-text-primary font-semibold">
                  {{ formatMoney(item.revenue_generated) }}
                </td>
                <td class="py-3 px-3 font-mono font-bold text-right text-emerald-700">
                  {{ formatMoney(item.owner_payout) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  AlertTriangle,
  ArrowRight,
  DollarSign,
  FileCheck,
  Layers,
  Loader2,
  TrendingUp,
  Users
} from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { ConsignmentDashboardResponse } from '@/api/contracts'
import { formatCurrency } from '@/utils/formatters'

const selectedPeriod = ref('2026-08')
const dashboard = ref<ConsignmentDashboardResponse | null>(null)
const isLoading = ref(true)
const errorMessage = ref('')

async function loadDashboard() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const client = getCortexApiClient()
    const res = await client.getConsignmentDashboard({
      period: selectedPeriod.value
    })
    dashboard.value = res
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors du chargement de la consignation.'
  } finally {
    isLoading.value = false
  }
}

function formatMoney(amount: number): string {
  return formatCurrency(amount)
}

onMounted(() => {
  loadDashboard()
})
</script>
