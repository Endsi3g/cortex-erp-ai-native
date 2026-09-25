<template>
  <div class="space-y-6 max-w-7xl mx-auto" data-test="screen-rental-detail">
    <!-- Top breadcrumb & navigation -->
    <div class="flex items-center justify-between">
      <RouterLink
        to="/rentals"
        class="text-xs text-cortex-text-muted hover:text-cortex-text-primary flex items-center gap-1 font-medium"
      >
        <ArrowLeft class="w-3.5 h-3.5" />
        <span>Retour aux Locations</span>
      </RouterLink>

      <button
        type="button"
        class="cx-btn-secondary text-xs px-2.5 py-1 flex items-center gap-1"
        :disabled="isLoading"
        @click="loadRental"
      >
        <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': isLoading }" />
        <span>Actualiser</span>
      </button>
    </div>

    <!-- Error Banner -->
    <CortexErrorBanner
      v-if="errorMessage"
      :error-message="errorMessage"
      @retry="loadRental"
    />

    <!-- Feedback Notice (e.g. approval required feedback) -->
    <div
      v-if="feedbackNotice"
      class="p-3.5 rounded-xl border border-amber-300 bg-amber-50 text-xs text-amber-950 flex items-center justify-between shadow-2xs"
      data-test="detail-feedback-notice"
    >
      <div class="flex items-center gap-2">
        <AlertCircle class="w-4 h-4 text-amber-600 flex-shrink-0" />
        <span>{{ feedbackNotice }}</span>
      </div>
      <RouterLink
        to="/approvals"
        class="cx-btn-secondary text-xs px-2.5 py-1 whitespace-nowrap"
      >
        Consulter la File SAS →
      </RouterLink>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="isLoading" class="space-y-4">
      <CortexSkeleton :lines="8" />
    </div>

    <!-- Rental Content -->
    <div v-else-if="rental" class="space-y-5">
      <!-- 1. Header Banner with Next Action CTA -->
      <RentalHeaderBanner
        :rental="rental"
        :is-action-loading="isActionLoading"
        @action="handleHeaderAction"
      />

      <!-- 2. Persistent Readiness Card -->
      <RentalReadinessCard :readiness="rental.readiness" />

      <!-- 3. 6 Canonical Tabs Navigation Bar -->
      <div class="border-b border-cortex-border">
        <nav class="flex items-center gap-1 -mb-px overflow-x-auto text-xs font-semibold" data-test="rental-detail-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 focus:outline-none"
            :class="activeTab === tab.id
              ? 'border-cortex-primary-600 text-cortex-primary-700 font-bold bg-cortex-primary-50/20'
              : 'border-transparent text-cortex-text-muted hover:text-cortex-text-primary hover:border-cortex-border'"
            :data-test="`tab-btn-${tab.id}`"
            @click="activeTab = tab.id"
          >
            <span>{{ tab.label }}</span>
          </button>
        </nav>
      </div>

      <!-- Tab Content Area -->
      <div class="pt-2">
        <TabOverview v-if="activeTab === 'overview'" :rental="rental" />
        <TabEquipmentSerials v-else-if="activeTab === 'equipment'" :rental="rental" />
        <TabDocsEvidence v-else-if="activeTab === 'docs'" :rental="rental" />
        <TabCheckinRestitution v-else-if="activeTab === 'checkin'" :rental="rental" />
        <TabFinancePnl v-else-if="activeTab === 'finance'" :rental="rental" />
        <TabAuditLog v-else-if="activeTab === 'audit'" :rental-id="rental.name" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, RefreshCw, AlertCircle } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { RentalTransaction } from '@/types/rental'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import RentalHeaderBanner from '../components/detail/RentalHeaderBanner.vue'
import RentalReadinessCard from '../components/detail/RentalReadinessCard.vue'
import TabOverview from '../components/detail/tabs/TabOverview.vue'
import TabEquipmentSerials from '../components/detail/tabs/TabEquipmentSerials.vue'
import TabDocsEvidence from '../components/detail/tabs/TabDocsEvidence.vue'
import TabCheckinRestitution from '../components/detail/tabs/TabCheckinRestitution.vue'
import TabFinancePnl from '../components/detail/tabs/TabFinancePnl.vue'
import TabAuditLog from '../components/detail/tabs/TabAuditLog.vue'

const { t } = useI18n()
const route = useRoute()

const rentalName = computed(() => String(route.params.name || 'DEMO-TRX-2026-001'))

const rental = ref<RentalTransaction | null>(null)
const isLoading = ref<boolean>(false)
const isActionLoading = ref<boolean>(false)
const errorMessage = ref<string | null>(null)
const feedbackNotice = ref<string | null>(null)
const activeTab = ref<string>('overview')

const tabs = computed(() => [
  { id: 'overview', label: t('rental_detail.tab_overview') },
  { id: 'equipment', label: t('rental_detail.tab_equipment') },
  { id: 'docs', label: t('rental_detail.tab_docs') },
  { id: 'checkin', label: t('rental_detail.tab_checkin') },
  { id: 'finance', label: t('rental_detail.tab_finance') },
  { id: 'audit', label: t('rental_detail.tab_audit') }
])

const loadRental = async () => {
  isLoading.value = true
  errorMessage.value = null
  try {
    const client = getCortexApiClient()
    const res = await client.getRental({ id: rentalName.value })
    rental.value = res
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors du chargement de la transaction'
  } finally {
    isLoading.value = false
  }
}

const handleHeaderAction = async (action: string) => {
  if (!rental.value) return
  isActionLoading.value = true
  feedbackNotice.value = null
  try {
    const client = getCortexApiClient()
    if (action === 'requestReservation') {
      const res = await client.requestReservation({
        rental_id: rental.value.id,
        version: rental.value.version
      })
      if (res.status === 'completed') {
        await loadRental()
      }
    } else if (action === 'requestContract') {
      const res = await client.requestContractApproval({
        rental_id: rental.value.id,
        version: rental.value.version
      })
      if (res.status === 'approval_required') {
        feedbackNotice.value = 'Le pré-requis d’assurance est incomplet : une demande d’approbation dérogatoire a été soumise au superviseur (DEMO-APR).'
      } else if (res.status === 'completed') {
        await loadRental()
      }
    }
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors de l’exécution de l’action'
  } finally {
    isActionLoading.value = false
  }
}

onMounted(() => {
  loadRental()
})
</script>
