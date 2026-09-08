import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCortexApiClient } from '@/api'

export const useApprovalsStore = defineStore('approvals', () => {
  const pendingCount = ref<number>(4)
  const pendingApprovalIds = ref<string[]>([
    'DEMO-APR-001',
    'DEMO-APR-002',
    'DEMO-APR-003',
    'DEMO-APR-004'
  ])
  const isLoading = ref<boolean>(false)

  const decrementCount = (id?: string) => {
    if (pendingCount.value > 0) {
      pendingCount.value--
    }
    if (id) {
      pendingApprovalIds.value = pendingApprovalIds.value.filter(item => item !== id)
    }
  }

  const incrementCount = () => {
    pendingCount.value++
  }

  const fetchPendingApprovals = async () => {
    isLoading.value = true
    try {
      const client = getCortexApiClient()
      const res = await client.listApprovalRequests({ status: 'pending' })
      pendingCount.value = res.total_count
      pendingApprovalIds.value = res.items.map(item => item.id)
    } catch {
      pendingCount.value = pendingApprovalIds.value.length
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
