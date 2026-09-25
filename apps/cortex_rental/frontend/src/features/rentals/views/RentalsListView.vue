<template>
  <div class="space-y-4 max-w-7xl mx-auto" data-test="screen-rentals-list">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-cortex-border">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-xl font-bold text-cortex-text-primary tracking-tight">
            {{ t('routes.rentals_list') }}
          </h1>
          <span class="px-2 py-0.5 rounded-full bg-cortex-primary-100 text-cortex-primary-800 text-[11px] font-semibold">
            {{ rentalsStore.rentals.length }} locations
          </span>
          <span class="px-2 py-0.5 rounded-full bg-cortex-surface-secondary border border-cortex-border text-cortex-text-muted text-[11px] font-mono">
            DEMO
          </span>
        </div>
        <p class="text-xs text-cortex-text-secondary mt-1">
          Master directory des soumissions, réservations, contrats et retours de location.
        </p>
      </div>

      <div class="flex items-center gap-2.5">
        <button
          type="button"
          class="cx-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
          :disabled="rentalsStore.isLoading"
          @click="loadRentals"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': rentalsStore.isLoading }" />
          <span>{{ t('ui_states.refresh') }}</span>
        </button>
        <RouterLink
          to="/rentals/new"
          class="cx-btn-primary text-xs px-3.5 py-1.5 flex items-center gap-1.5"
          data-test="new-rental-btn"
        >
          <PlusCircle class="w-3.5 h-3.5" />
          <span>{{ t('rentals.new_rental') }}</span>
        </RouterLink>
      </div>
    </div>

    <!-- Search & Filter Controls -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs">
      <!-- Status Filter Chips -->
      <RentalStatusFilterBar
        :selected-state="rentalsStore.activeStateFilter"
        :counts="statusCounts"
        @update:selected-state="handleStateChange"
      />

      <!-- Search Input with 250ms debounce -->
      <div class="relative min-w-[240px]">
        <input
          v-model="searchInput"
          type="text"
          :placeholder="t('rentals.search_placeholder')"
          class="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary placeholder:text-cortex-text-muted focus:outline-none focus:ring-1 focus:ring-cortex-primary-500"
          data-test="rentals-search-input"
        />
        <Search class="w-4 h-4 absolute left-2.5 top-2 text-cortex-text-muted pointer-events-none" />
      </div>
    </div>

    <!-- Error Banner -->
    <CortexErrorBanner
      v-if="rentalsStore.error"
      :error-message="rentalsStore.error"
      @retry="loadRentals"
    />

    <!-- Rentals Table -->
    <div class="bg-cortex-surface rounded-xl border border-cortex-border shadow-2xs overflow-hidden">
      <CortexTable
        :columns="tableColumns"
        :rows="tableRows"
        row-key="id"
        :loading="rentalsStore.isLoading"
        :empty-text="t('ui_states.empty')"
        @row-click="handleRowClick"
      >
        <!-- Custom cell: Transaction ID -->
        <template #cell-id="{ row }">
          <span class="font-mono font-bold text-xs text-cortex-primary-700 hover:underline">
            {{ row.id }}
          </span>
        </template>

        <!-- Custom cell: Customer & Project -->
        <template #cell-customer="{ row }">
          <div class="min-w-0">
            <span class="font-semibold text-xs text-cortex-text-primary block truncate">
              {{ row.customer_name }}
            </span>
            <span v-if="row.project_name" class="text-[11px] text-cortex-text-muted block truncate">
              {{ row.project_name }}
            </span>
          </div>
        </template>

        <!-- Custom cell: State badge -->
        <template #cell-state="{ row }">
          <CortexBadge :state="mapStateToBadge(row.rental_state)" size="sm" />
        </template>

        <!-- Custom cell: Dates -->
        <template #cell-dates="{ row }">
          <span class="font-mono text-xs text-cortex-text-secondary whitespace-nowrap">
            {{ formatDateRange(row.starts_at, row.ends_at) }}
          </span>
        </template>

        <!-- Custom cell: Billable Days -->
        <template #cell-billable_days="{ row }">
          <span class="font-mono text-xs text-cortex-text-primary" title="Règle 7j = 3j">
            <strong>{{ row.billable_days }}j</strong> / {{ row.calendar_days }}j
          </span>
        </template>

        <!-- Custom cell: Grand Total -->
        <template #cell-grand_total="{ row }">
          <span class="font-mono font-bold text-xs text-cortex-text-primary">
            {{ formatCurrency(row.grand_total) }}
          </span>
        </template>

        <!-- Custom cell: Actions -->
        <template #cell-actions="{ row }">
          <div class="flex items-center justify-end gap-1.5" @click.stop>
            <RouterLink
              :to="`/rentals/${row.name}`"
              class="cx-btn-secondary text-[11px] px-2 py-1"
              data-test="action-view-360"
            >
              {{ t('rentals.action_view') }}
            </RouterLink>

            <!-- Contextual Check-out -->
            <RouterLink
              v-if="row.rental_state === 'Contract' || row.rental_state === 'Reservation'"
              :to="`/checkout/${row.name}`"
              class="cx-btn-primary text-[11px] px-2 py-1"
              data-test="action-checkout"
            >
              {{ t('rentals.action_checkout') }}
            </RouterLink>

            <!-- Contextual Check-in -->
            <RouterLink
              v-else-if="row.rental_state === 'Checked Out' || row.rental_state === 'Partially Returned'"
              :to="`/checkin/${row.name}`"
              class="cx-btn-secondary text-[11px] px-2 py-1 border-amber-300 text-amber-900 bg-amber-50 hover:bg-amber-100"
              data-test="action-checkin"
            >
              {{ t('rentals.action_checkin') }}
            </RouterLink>
          </div>
        </template>
      </CortexTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { RefreshCw, PlusCircle, Search } from 'lucide-vue-next'
import type { RentalState, RentalTransaction } from '@/types/rental'
import { useRentalsStore } from '@/stores/rentals'
import CortexTable, { type TableColumn } from '@/design-system/components/base/CortexTable.vue'
import CortexBadge from '@/design-system/components/base/CortexBadge.vue'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import RentalStatusFilterBar from '../components/RentalStatusFilterBar.vue'

const { t } = useI18n()
const router = useRouter()
const rentalsStore = useRentalsStore()

const searchInput = ref<string>('')
const allRentals = ref<RentalTransaction[]>([])

const tableColumns: TableColumn[] = [
  { key: 'id', label: 'ID Transaction', width: '160px', isMono: true, sortable: true },
  { key: 'customer', label: 'Client & Projet', sortable: true },
  { key: 'state', label: 'Statut', width: '130px', align: 'center' },
  { key: 'dates', label: 'Période', width: '170px', align: 'center' },
  { key: 'billable_days', label: 'Jours facturés', width: '110px', align: 'center' },
  { key: 'grand_total', label: 'Total TTC (CAD)', width: '130px', align: 'right', isMono: true, sortable: true },
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
  router.push(`/rentals/${row.name || row.id}`)
}

onMounted(() => {
  loadRentals()
})
</script>
