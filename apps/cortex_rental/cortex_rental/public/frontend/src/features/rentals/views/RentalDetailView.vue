<template>
  <div class="cx-page" data-test="screen-rental-detail">
    <CortexPageHeader :title="rental?.name ?? rentalName" :provenance="rental?.provenance">
      <template #actions>
        <RouterLink to="/app/cortex-rentals" class="cx-btn-soft">Toutes les locations</RouterLink>
        <RefreshButton :loading="isLoading" @refresh="loadRental" />
        <RentalNextAction v-if="rental" :rental="rental" :is-action-loading="isActionLoading" @action="handleHeaderAction" />
      </template>
    </CortexPageHeader>

    <div v-if="errorMessage" class="cx-section"><CortexErrorBanner :error-message="errorMessage" @retry="loadRental" /></div>

    <div v-if="feedbackNotice" class="cx-notice" role="status" data-test="detail-feedback-notice">
      <span>{{ feedbackNotice }}</span>
      <RouterLink to="/app/cortex-ai-inbox?type=approval" class="cx-btn-soft">Ouvrir les approbations</RouterLink>
    </div>

    <div v-if="isLoading && !rental" class="cx-section"><CortexSkeleton :lines="8" /></div>

    <template v-else-if="rental">
      <RentalHeaderBanner :rental="rental" />
      <RentalReadinessCard :readiness="rental.readiness" />

      <div class="cx-tabs mt-6" role="tablist" data-test="rental-detail-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          role="tab"
          class="cx-tab"
          :aria-selected="activeTab === tab.id"
          :data-test="`tab-btn-${tab.id}`"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <div class="cx-section" role="tabpanel">
        <TabOverview v-if="activeTab === 'overview'" :rental="rental" />
        <TabEquipmentSerials v-else-if="activeTab === 'equipment'" :rental="rental" />
        <TabDocsEvidence v-else-if="activeTab === 'docs'" :rental="rental" />
        <TabCheckinRestitution v-else-if="activeTab === 'checkin'" :rental="rental" />
        <TabFinancePnl v-else-if="activeTab === 'finance'" :rental="rental" />
        <TabAuditLog v-else-if="activeTab === 'audit'" :rental-id="rental.name" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getCortexApiClient } from '@/api'
import type { RentalTransaction } from '@/types/rental'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import RentalNextAction from '../components/detail/RentalNextAction.vue'
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

const rentalName = computed(() => String(route.params.name || ''))

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
        feedbackNotice.value = `Le pré-requis d’assurance est incomplet: une demande d’approbation dérogatoire a été soumise${res.approval_request_id ? ` (${res.approval_request_id})` : ''}.`
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
