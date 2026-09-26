import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCortexApiClient } from '@/api'

export const useApprovalsStore = defineStore('approvals', () => {
  // null = not known yet (never fetched, or the API refused/failed).
  // The UI must not show a count it has not read from the server.
  const pendingCount = ref<number | null>(null)
  const pendingApprovalIds = ref<string[]>([])
  const isLoading = ref<boolean>(false)

  const decrementCount = (id?: string) => {
    if (pendingCount.value !== null && pendingCount.value > 0) {
      pendingCount.value--
    }
    if (id) {
      pendingApprovalIds.value = pendingApprovalIds.value.filter(item => item !== id)
    }
  }

  const incrementCount = () => {
    if (pendingCount.value !== null) pendingCount.value++
  }

  const fetchPendingApprovals = async () => {
    isLoading.value = true
    try {
      const client = getCortexApiClient()
      const res = await client.listApprovalRequests({ status: 'pending' })
      pendingCount.value = res.total_count
      pendingApprovalIds.value = res.items.map(item => item.id)
    } catch {
      pendingCount.value = null
      pendingApprovalIds.value = []
    } finally {
      isLoading.value = false
    }
  }

  return {
    pendingCount,
    pendingApprovalIds,
    isLoading,
    decrementCount,
    incrementCount,
    fetchPendingApprovals
  }
})
