<template>
  <div class="cx-page" data-test="screen-rentals-list">
    <CortexPageHeader :title="t('routes.rentals_list')" subtitle="Soumissions, réservations, contrats et retours de location." :provenance="rentalsStore.rentals[0]?.provenance">
      <template #actions>
        <RefreshButton :loading="rentalsStore.isLoading" @refresh="loadRentals" />
        <RouterLink to="/app/cortex-rental/new" class="cx-btn-primary" data-test="new-rental-btn">{{ t('rentals.new_rental') }}</RouterLink>
      </template>
    </CortexPageHeader>

    <div class="cx-filters">
      <FilterField label="Rechercher une location">
        <input v-model="searchInput" type="search" class="cx-field" :placeholder="t('rentals.search_placeholder')" data-test="rentals-search-input" />
      </FilterField>
      <RentalStatusFilterBar :selected-state="rentalsStore.activeStateFilter" :counts="statusCounts" @update:selected-state="handleStateChange" />
    </div>

    <div v-if="rentalsStore.error" class="cx-section"><CortexErrorBanner :error-message="rentalsStore.error" @retry="loadRentals" /></div>

    <CortexTable
      :columns="tableColumns"
      :rows="tableRows"
      row-key="id"
      :loading="rentalsStore.isLoading"
      :empty-text="t('ui_states.empty')"
      @row-click="handleRowClick"
    >
      <template #cell-state="{ row }">
        <CortexBadge :variant="mapStateToBadge(row.rental_state)" size="sm" />
      </template>

      <template #cell-customer="{ row }">
        <div class="font-medium">{{ row.customer_name }}</div>
        <div v-if="row.project_name" style="color: #666666; font-size: 13px">{{ row.project_name }}</div>
      </template>

      <template #cell-dates="{ row }">{{ formatDateRange(row.starts_at, row.ends_at) }}</template>

      <template #cell-billable_days="{ row }">{{ row.billable_days }}</template>

      <template #cell-grand_total="{ row }">{{ formatCurrency(row.grand_total) }}</template>

      <template #cell-actions="{ row }">
        <div class="flex items-center justify-end gap-2" @click.stop>
          <RouterLink :to="`/app/cortex-rental/${row.name}`" class="cx-btn-soft" data-test="action-view-360">{{ t('rentals.action_view') }}</RouterLink>
          <RouterLink v-if="row.rental_state === 'Contract' || row.rental_state === 'Reservation'" :to="`/app/cortex-checkout/${row.name}`" class="cx-btn-primary" data-test="action-checkout">{{ t('rentals.action_checkout') }}</RouterLink>
          <RouterLink v-else-if="row.rental_state === 'Checked Out'" :to="`/app/cortex-checkin/${row.name}`" class="cx-btn-soft" data-test="action-checkin">{{ t('rentals.action_checkin') }}</RouterLink>
        </div>
      </template>
    </CortexTable>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { RentalState, RentalTransaction } from '@/types/rental'
import { useRentalsStore } from '@/stores/rentals'
import CortexTable, { type TableColumn } from '@/design-system/components/base/CortexTable.vue'
import CortexBadge from '@/design-system/components/base/CortexBadge.vue'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import RentalStatusFilterBar from '../components/RentalStatusFilterBar.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import FilterField from '@/features/common/components/FilterField.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const rentalsStore = useRentalsStore()

const searchInput = ref<string>('')
const allRentals = ref<RentalTransaction[]>([])

const tableColumns: TableColumn[] = [
  { key: 'id', label: 'Transaction', width: '170px', isMono: true, sortable: true },
  { key: 'customer', label: 'Client et projet', sortable: true },
  { key: 'state', label: 'Statut', width: '130px', align: 'center' },
  { key: 'dates', label: 'Période', width: '170px', align: 'center' },
  { key: 'billable_days', label: 'Jours facturés', width: '110px', align: 'center' },
  { key: 'grand_total', label: 'Total taxes incluses', width: '150px', align: 'right', isMono: true, sortable: true },
  { key: 'actions', label: 'Actions', width: '160px', align: 'right' }
]

const loadRentals = async () => {
  const items = await rentalsStore.fetchRentals()
  if (items && items.length > 0) {
    allRentals.value = items
  }
}

const handleStateChange = (state: RentalState | 'all') => {
  rentalsStore.setStateFilter(state)
  rentalsStore.fetchRentals(state)
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchInput, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    rentalsStore.setSearchQuery(val)
    rentalsStore.fetchRentals(undefined, val)
  }, 250)
})

const tableRows = computed(() => {
  return rentalsStore.rentals.map((r) => ({
    ...r,
    customer: r.customer_name,
    state: r.rental_state,
    dates: `${r.starts_at} - ${r.ends_at}`
  }))
})

const statusCounts = computed(() => {
  const counts: Record<string, number> = { all: allRentals.value.length }
  for (const r of allRentals.value) {
    counts[r.rental_state] = (counts[r.rental_state] || 0) + 1
  }
  return counts
})

const mapStateToBadge = (state: RentalState): 'quote' | 'reservation' | 'contract' | 'checked_out' | 'partial_return' | 'returned' | 'invoiced' | 'cancelled' | 'draft' => {
  switch (state) {
    case 'Quote': return 'quote'
    case 'Reservation': return 'reservation'
    case 'Contract': return 'contract'
    case 'Checked Out': return 'checked_out'
    case 'Partially Returned': return 'partial_return'
    case 'Returned': return 'returned'
    case 'Invoiced': return 'invoiced'
    case 'Cancelled': return 'cancelled'
    default: return 'draft'
  }
}

const formatDateRange = (startsAt: string, endsAt: string) => {
  try {
    const s = new Date(startsAt)
    const e = new Date(endsAt)
    return `${s.getDate()}/${s.getMonth() + 1} → ${e.getDate()}/${e.getMonth() + 1}`
  } catch {
    return `${startsAt} → ${endsAt}`
  }
}

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amount)
}

const handleRowClick = (row: Record<string, any>) => {
  router.push(`/app/cortex-rental/${row.name || row.id}`)
}

onMounted(() => {
  // Deep links such as /app/cortex-rentals?state=Checked Out from the operations cockpit.
  const requested = route.query.state
  if (typeof requested === 'string' && requested) rentalsStore.setStateFilter(requested as RentalState)
  loadRentals()
})
</script>
