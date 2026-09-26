import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCortexApiClient } from '@/api'
import type { RentalTransaction, RentalState } from '@/types/rental'

export const useRentalsStore = defineStore('rentals', () => {
  const activeStateFilter = ref<RentalState | 'all'>('all')
  const searchQuery = ref<string>('')
  const rentals = ref<RentalTransaction[]>([])
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  const fetchRentals = async (stateFilter?: RentalState | 'all', query?: string) => {
    isLoading.value = true
    error.value = null
    try {
      const client = getCortexApiClient()
      const effectiveState = stateFilter !== undefined ? stateFilter : activeStateFilter.value
      const effectiveQuery = query !== undefined ? query : searchQuery.value

      const res = await client.listRentals({
        page: 1,
        page_size: 50,
        state: effectiveState === 'all' ? undefined : effectiveState,
        search: effectiveQuery ? effectiveQuery : undefined
      })
      rentals.value = res.items
      return res.items
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du chargement des locations'
      return []
    } finally {
      isLoading.value = false
    }
  }

  const setStateFilter = (state: RentalState | 'all') => {
    activeStateFilter.value = state
  }

  const setSearchQuery = (query: string) => {
    searchQuery.value = query
  }

  return {
    activeStateFilter,
    searchQuery,
    rentals,
    isLoading,
    error,
    fetchRentals,
    setStateFilter,
    setSearchQuery
  }
})
