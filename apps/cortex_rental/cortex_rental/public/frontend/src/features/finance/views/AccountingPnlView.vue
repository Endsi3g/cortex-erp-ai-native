<template>
  <div class="cx-page" data-test="screen-accounting-pnl">
    <CortexPageHeader title="État des résultats" subtitle="Rapport « Profit and Loss Statement » d'ERPNext, sans recalcul." :provenance="data?.provenance">
      <template #actions>
        <a class="cx-btn-secondary" href="/app/query-report/Profit%20and%20Loss%20Statement">Ouvrir le rapport ERPNext</a>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <form class="cx-filters" @submit.prevent="reload">
      <FilterField label="Exercice fiscal">
        <select v-model="fiscalYear" class="cx-field" @change="reload">
          <option v-for="year in years" :key="year" :value="year">{{ year }}</option>
        </select>
      </FilterField>
      <FilterField label="Périodicité">
        <select v-model="periodicity" class="cx-field" @change="reload">
          <option value="Monthly">Mensuelle</option>
          <option value="Quarterly">Trimestrielle</option>
          <option value="Half-Yearly">Semestrielle</option>
          <option value="Yearly">Annuelle</option>
        </select>
      </FilterField>
      <FilterField label="Valeurs cumulées">
        <label class="cx-check"><input v-model="accumulated" type="checkbox" @change="reload" /> Cumuler les périodes</label>
      </FilterField>
    </form>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-else-if="loading && !data" class="cx-section"><CortexSkeleton variant="table-row" :count="6" /></div>
    <div v-else-if="data?.reportError" class="cx-section">
      <div class="cx-notice" role="alert">
        <div>
          <strong>Le rapport ERPNext n'a pas pu être produit.</strong>
          <p class="m-0 mt-1">{{ data.reportError }}</p>
          <p class="m-0 mt-1">Aucun montant n'est affiché : ce n'est pas un résultat de zéro.</p>
        </div>
      </div>
    </div>
    <template v-else-if="data">
      <KpiStrip :items="kpis" :operators="['−', '=']" />

      <section v-if="data.periods.length > 1" class="cx-section" aria-labelledby="pnl-chart">
        <h2 id="pnl-chart">Résultat net par période</h2>
        <svg class="cx-chart" :viewBox="`0 0 ${chart.width} ${chart.height}`" role="img" :aria-label="`Résultat net par période, de ${chart.min} à ${chart.max}`">
          <line :x1="0" :x2="chart.width" :y1="chart.zeroY" :y2="chart.zeroY" class="cx-chart__axis" />
          <polyline :points="chart.points" class="cx-chart__line" fill="none" />
          <circle v-for="dot in chart.dots" :key="dot.key" :cx="dot.x" :cy="dot.y" r="3" class="cx-chart__dot"><title>{{ dot.label }} : {{ dot.value }}</title></circle>
        </svg>
      </section>

      <div v-if="!rows.length" class="cx-empty"><strong>Aucune écriture</strong>Aucun compte de résultat pour cette période.</div>
      <div v-else class="cx-tablewrap">
        <table class="cx-table">
          <thead>
            <tr>
              <th scope="col">Compte</th>
              <th v-for="period in data.periods" :key="period.key" scope="col" class="num">{{ period.label }}</th>
              <th scope="col" class="num">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.node.id" :class="{ 'cx-row--group': row.node.type === 'group' }">
              <td :style="{ paddingLeft: `${12 + row.node.depth * 20}px` }">
                <button v-if="row.node.children.length" type="button" class="cx-chevron" :aria-expanded="isOpen(row.node.id)" :aria-label="`${isOpen(row.node.id) ? 'Réduire' : 'Développer'} ${row.node.name}`" @click="toggle(row.node.id)">
                  <span aria-hidden="true">{{ isOpen(row.node.id) ? '▾' : '▸' }}</span>
                </button>
                <span v-else class="cx-chevron" aria-hidden="true" />
                {{ row.node.name }}
              </td>
              <td v-for="period in data.periods" :key="period.key" class="num">{{ money(row.node.values[period.key]) }}</td>
              <td class="num">{{ money(row.node.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { getCortexApiClient } from '@/api'
import type { PnlAccountNode } from '@/api/contracts'
import { formatCurrency } from '@/utils/currency'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import FilterField from '@/features/common/components/FilterField.vue'
import KpiStrip, { type KpiItem } from '@/features/common/components/KpiStrip.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

const thisYear = new Date().getFullYear()
const years = [thisYear, thisYear - 1, thisYear - 2].map(String)
const fiscalYear = ref(years[0])
const periodicity = ref<'Monthly' | 'Quarterly' | 'Half-Yearly' | 'Yearly'>('Monthly')
const accumulated = ref(false)

const { data, loading, error, reload } = useResource(() =>
  getCortexApiClient().getProfitAndLoss({ fiscal_year: fiscalYear.value, periodicity: periodicity.value, accumulated_values: accumulated.value })
)

const closed = reactive(new Set<string>())
const isOpen = (id: string) => !closed.has(id)
const toggle = (id: string) => (closed.has(id) ? closed.delete(id) : closed.add(id))
const money = (value: number | null | undefined) => (value === null || value === undefined ? '' : formatCurrency(value))

const rows = computed(() => {
  const out: Array<{ node: PnlAccountNode }> = []
  const walk = (nodes: PnlAccountNode[]) => {
    for (const node of nodes) {
      out.push({ node })
      if (isOpen(node.id)) walk(node.children)
    }
  }
  walk(data.value?.accounts ?? [])
  return out
})

const kpis = computed<KpiItem[]>(() => {
  const report = data.value
  if (!report) return []
  return [
    { key: 'income', label: 'Total des revenus', value: formatCurrency(report.totalIncome) },
    { key: 'expense', label: 'Total des dépenses', value: formatCurrency(report.totalExpense) },
    { key: 'net', label: 'Bénéfice net', value: formatCurrency(report.netProfit), positive: report.netProfit > 0 }
  ]
})

const chart = computed(() => {
  const periods = data.value?.periods ?? []
  const width = 640
  const height = 160
  const values = periods.map((period) => period.profitLoss)
  const max = Math.max(0, ...values)
  const min = Math.min(0, ...values)
  const span = max - min || 1
  const y = (value: number) => 12 + (height - 24) * (1 - (value - min) / span)
  const x = (index: number) => 12 + ((width - 24) * index) / Math.max(1, periods.length - 1)
  const dots = periods.map((period, index) => ({ key: period.key, label: period.label, value: formatCurrency(period.profitLoss), x: x(index), y: y(period.profitLoss) }))
  return { width, height, min, max, zeroY: y(0), dots, points: dots.map((dot) => `${dot.x},${dot.y}`).join(' ') }
})
</script>
