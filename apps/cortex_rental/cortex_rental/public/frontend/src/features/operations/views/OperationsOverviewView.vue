<template>
  <div class="space-y-6 max-w-7xl mx-auto" data-test="screen-operations-overview">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-cortex-border">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-xl font-bold text-cortex-text-primary tracking-tight">
            {{ t('routes.operations_overview') }}
          </h1>
          <span class="px-2 py-0.5 rounded-full bg-cortex-primary-100 text-cortex-primary-800 text-[11px] font-semibold">
            Cockpit Journalier
          </span>
          <span class="px-2 py-0.5 rounded-full bg-cortex-surface-secondary border border-cortex-border text-cortex-text-muted text-[11px] font-mono">
            DEMO
          </span>
        </div>
        <p class="text-xs text-cortex-text-secondary mt-1">
          Supervision en temps réel des départs, retours et alertes de flotte pour aujourd'hui.
        </p>
      </div>

      <div class="flex items-center gap-2.5">
        <button
          class="cx-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
          :disabled="isLoading"
          @click="loadData"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': isLoading }" />
          <span>{{ t('ui_states.refresh') }}</span>
        </button>
        <RouterLink
          to="/app/cortex-rental/new"
          class="cx-btn-primary text-xs px-3.5 py-1.5 flex items-center gap-1.5"
        >
          <PlusCircle class="w-3.5 h-3.5" />
          <span>{{ t('rentals.new_rental') }}</span>
        </RouterLink>
      </div>
    </div>

    <!-- Error Banner if any -->
    <CortexErrorBanner
      v-if="errorMessage"
      :error-message="errorMessage"
      @retry="loadData"
    />

    <!-- KPI Cards (4 Clickable Filters) -->
    <OperationsKpiCards
      v-model:active-filter="activeFilter"
      :departures-count="kpiCounts.departures"
      :returns-count="kpiCounts.returns"
      :exceptions-count="kpiCounts.exceptions"
      :approvals-count="kpiCounts.approvals"
    />

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left (2 Cols): Timeline -->
      <div class="lg:col-span-2">
        <OperationsTimeline :active-filter="activeFilter" />
      </div>

      <!-- Right (1 Col): Attention Required & AI Intake -->
      <div class="space-y-6">
        <OperationsAttentionRequired />
        <OperationsIncomingWidget />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RefreshCw, PlusCircle } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import OperationsKpiCards, { type OperationsFilter } from '../components/OperationsKpiCards.vue'
import OperationsTimeline from '../components/OperationsTimeline.vue'
import OperationsAttentionRequired from '../components/OperationsAttentionRequired.vue'
import OperationsIncomingWidget from '../components/OperationsIncomingWidget.vue'

const { t } = useI18n()

const isLoading = ref<boolean>(false)
const errorMessage = ref<string | null>(null)
const activeFilter = ref<OperationsFilter>('all')

const kpiCounts = reactive({
  departures: 8,
  returns: 11,
  exceptions: 3,
  approvals: 4
})

const loadData = async () => {
  isLoading.value = true
  errorMessage.value = null
  try {
    const client = getCortexApiClient()
    // Fetch pending approvals to synchronize count
    const approvalsRes = await client.listApprovalRequests({ status: 'pending' })
    if (approvalsRes && typeof approvalsRes.total_count === 'number') {
      kpiCounts.approvals = approvalsRes.total_count
    }
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur de synchronisation du cockpit'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
