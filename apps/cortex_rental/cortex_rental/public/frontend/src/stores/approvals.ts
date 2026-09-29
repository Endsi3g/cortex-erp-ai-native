import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCortexApiClient } from '@/api'

export const useApprovalsStore = defineStore('approvals', () => {
  // Unknown (null) until the server has answered: the shell shows no badge rather than an invented count.
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
    pendingCount.value = (pendingCount.value ?? 0) + 1
  }

  const fetchPendingApprovals = async () => {
    isLoading.value = true
    try {
      const client = getCortexApiClient()
      const res = await client.listApprovalRequests({ status: 'pending' })
      pendingCount.value = res.total_count
      pendingApprovalIds.value = res.items.map(item => item.id)
    } catch {
      // Keep the last known value: a failed refresh must not turn into "0 pending".
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
