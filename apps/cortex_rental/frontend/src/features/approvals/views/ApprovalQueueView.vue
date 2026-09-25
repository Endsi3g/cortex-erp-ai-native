<template>
  <div class="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-bold text-cortex-text-primary">
            {{ $t('approvals.title', 'Approval Queue — SAS d’Approbation Humaine') }}
          </h1>
          <span class="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
            F12 • R5
          </span>
        </div>
        <p class="text-xs text-cortex-text-muted mt-0.5">
          {{ $t('approvals.subtitle', 'Supervision humaine obligatoire pour actions engageantes, dérogations tarifaires et avenants IA') }}
        </p>
      </div>

      <!-- Live Pending Counter Badge -->
      <div class="flex items-center gap-2">
        <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs font-bold">
          <Lock class="w-3.5 h-3.5 text-amber-600" />
          <span>{{ pendingCount }} en attente</span>
        </span>
      </div>
    </div>

    <!-- Filter Bar & Search -->
    <div class="flex flex-wrap items-center justify-between gap-3 p-3 bg-cortex-surface rounded-2xl border border-cortex-border">
      <!-- Status Tabs -->
      <div class="flex items-center gap-1 bg-cortex-surface-muted p-1 rounded-xl">
        <button
          v-for="tab in filterTabs"
          :key="tab.value"
          type="button"
          class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all min-h-[36px] flex items-center gap-1.5"
          :class="
            activeFilter === tab.value
              ? 'bg-cortex-surface text-cortex-text-primary shadow-xs font-bold'
              : 'text-cortex-text-muted hover:text-cortex-text-primary'
          "
          @click="setFilter(tab.value)"
        >
          <span>{{ tab.label }}</span>
          <span
            v-if="tab.count !== undefined"
            class="text-[10px] font-mono px-1.5 py-0.2 rounded-full"
            :class="activeFilter === tab.value ? 'bg-amber-100 text-amber-900' : 'bg-cortex-surface text-cortex-text-muted'"
          >
            {{ tab.count }}
          </span>
        </button>
      </div>

      <!-- Search Input -->
      <div class="relative min-w-[240px] max-w-xs w-full">
        <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-cortex-text-muted" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher par titre, ID ou client..."
          class="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-cortex-border bg-cortex-surface-muted text-cortex-text-primary focus:outline-none focus:ring-2 focus:ring-cortex-primary/30 min-h-[36px]"
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="p-12 text-center text-cortex-text-muted bg-cortex-surface rounded-2xl border border-cortex-border">
      <Loader2 class="w-8 h-8 animate-spin mx-auto text-cortex-primary mb-2" />
      <span class="text-xs font-semibold">Chargement de la file de supervision...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage" class="p-6 rounded-2xl border border-red-200 bg-red-50 text-red-900">
      <div class="flex items-center gap-2 font-bold text-sm">
        <AlertTriangle class="w-5 h-5 text-red-600" />
        <span>Erreur de chargement</span>
      </div>
      <p class="text-xs text-red-800 mt-1">{{ errorMessage }}</p>
    </div>

    <!-- Main Split View (Master-Detail) -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <!-- Master List (Left Column) -->
      <div
        class="lg:col-span-5 space-y-3"
        :class="{ 'hidden lg:block': mobileShowDetail }"
      >
        <div v-if="filteredApprovals.length === 0" class="p-8 text-center bg-cortex-surface rounded-2xl border border-cortex-border space-y-2">
          <ShieldCheck class="w-10 h-10 mx-auto text-cortex-text-muted/50" />
          <div class="text-sm font-bold text-cortex-text-primary">Aucune demande d'approbation</div>
          <p class="text-xs text-cortex-text-muted max-w-xs mx-auto">
            Toutes les demandes de cette catégorie ont été traitées ou aucun résultat ne correspond à votre recherche.
          </p>
        </div>

        <div
          v-for="item in filteredApprovals"
          :key="item.id"
          class="p-4 rounded-2xl border transition-all cursor-pointer text-left space-y-2.5"
          :class="
            selectedApproval?.id === item.id
              ? 'border-cortex-primary bg-cortex-primary/5 ring-1 ring-cortex-primary shadow-xs'
              : 'border-cortex-border bg-cortex-surface hover:border-cortex-border-hover hover:bg-cortex-surface-muted/30'
          "
          @click="selectApproval(item)"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-[11px] font-mono font-bold text-cortex-text-muted">
              {{ item.id }}
            </span>
            <span
              class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
              :class="getStatusBadgeClass(item.status)"
            >
              {{ getStatusLabel(item.status) }}
            </span>
          </div>

          <div class="text-sm font-bold text-cortex-text-primary line-clamp-1">
            {{ item.title }}
          </div>

          <p class="text-xs text-cortex-text-muted line-clamp-2 leading-relaxed">
            {{ item.description }}
          </p>

          <div class="flex items-center justify-between text-[11px] pt-1 border-t border-cortex-border/50 text-cortex-text-muted">
            <div class="flex items-center gap-1.5">
              <Sparkles v-if="item.requested_by_type === 'Agent'" class="w-3.5 h-3.5 text-purple-600" />
              <User v-else class="w-3.5 h-3.5 text-slate-500" />
              <span>{{ item.requested_by_type === 'Agent' ? 'Agent IA' : 'Humain' }}</span>
            </div>
            <span class="font-mono">{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Detail Panel (Right Column) -->
      <div
        class="lg:col-span-7"
        :class="{ 'hidden lg:block': !mobileShowDetail && !selectedApproval }"
      >
        <div v-if="selectedApproval" class="sticky top-6">
          <ApprovalDetailPanel
            :approval="selectedApproval"
            :show-close="true"
            @approved="handleApprovalDecided"
            @rejected="handleRejectionDecided"
            @close="mobileShowDetail = false"
          />
        </div>

        <div v-else class="p-12 text-center bg-cortex-surface rounded-2xl border border-cortex-border text-cortex-text-muted space-y-2">
          <Eye class="w-10 h-10 mx-auto text-cortex-text-muted/40" />
          <div class="text-sm font-bold text-cortex-text-primary">Sélectionnez une demande</div>
          <p class="text-xs text-cortex-text-muted">
            Cliquez sur un élément de la liste pour inspecter le diff, les preuves et statuer.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  AlertTriangle,
  Eye,
  Loader2,
  Lock,
  Search,
  ShieldCheck,
  Sparkles,
  User
} from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { ApprovalRequestItem, ApprovalStatus } from '@/api/contracts'
import { useApprovalsStore } from '@/stores/approvals'
import ApprovalDetailPanel from '../components/ApprovalDetailPanel.vue'

const approvalsStore = useApprovalsStore()

const approvals = ref<ApprovalRequestItem[]>([])
const selectedApproval = ref<ApprovalRequestItem | null>(null)
const isLoading = ref(true)
const errorMessage = ref('')

const activeFilter = ref<'pending' | 'approved' | 'rejected' | 'all'>('pending')
const searchQuery = ref('')
const mobileShowDetail = ref(false)

const pendingCount = computed(() => {
  return approvals.value.filter(a => a.status === 'pending').length
})

const filterTabs = computed<Array<{ value: 'pending' | 'approved' | 'rejected' | 'all'; label: string; count?: number }>>(() => [
  { value: 'pending', label: 'En Attente', count: pendingCount.value },
  { value: 'approved', label: 'Approuvées' },
  { value: 'rejected', label: 'Rejetées' },
  { value: 'all', label: 'Toutes' }
])

const filteredApprovals = computed(() => {
  return approvals.value.filter(item => {
    // Status filter
    if (activeFilter.value !== 'all' && item.status !== activeFilter.value) {
      return false
    }

    // Search filter
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const matchTitle = item.title.toLowerCase().includes(q)
      const matchId = item.id.toLowerCase().includes(q)
      const matchReq = item.requested_by.toLowerCase().includes(q)
      const matchRef = item.reference_name.toLowerCase().includes(q)
      if (!matchTitle && !matchId && !matchReq && !matchRef) return false
    }

    return true
  })
})

async function fetchApprovals() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const client = getCortexApiClient()
    // Fetch all statuses so client-side tabs are snappy
    const res = await client.listApprovalRequests({
      status: undefined,
      page_size: 50
    })
    approvals.value = res.items

    // If previously selected approval exists, refresh it
    if (selectedApproval.value) {
      const refreshed = res.items.find(i => i.id === selectedApproval.value?.id)
      if (refreshed) {
        selectedApproval.value = refreshed
      }
    } else {
      // Default to first pending item
      const firstPending = res.items.find(i => i.status === 'pending')
      if (firstPending) {
        selectedApproval.value = firstPending
      } else if (res.items.length > 0) {
        selectedApproval.value = res.items[0]
      }
    }
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors du chargement des approbations.'
  } finally {
    isLoading.value = false
  }
}

function setFilter(filter: 'pending' | 'approved' | 'rejected' | 'all') {
  activeFilter.value = filter
  // Reset selected item if not in filtered list
  const inList = filteredApprovals.value.find(i => i.id === selectedApproval.value?.id)
  if (!inList && filteredApprovals.value.length > 0) {
    selectedApproval.value = filteredApprovals.value[0]
  }
}

function selectApproval(item: ApprovalRequestItem) {
  selectedApproval.value = item
  mobileShowDetail.value = true
}

async function handleApprovalDecided() {
  await fetchApprovals()
  await approvalsStore.fetchPendingApprovals()
}

async function handleRejectionDecided() {
  await fetchApprovals()
  await approvalsStore.fetchPendingApprovals()
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('fr-CA', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

function getStatusLabel(status: ApprovalStatus): string {
  switch (status) {
    case 'pending': return 'En Attente'
    case 'approved': return 'Approuvé'
    case 'rejected': return 'Rejeté'
    case 'expired': return 'Expiré'
    default: return status
  }
}

function getStatusBadgeClass(status: ApprovalStatus): string {
  switch (status) {
    case 'pending': return 'bg-amber-100 text-amber-900 border border-amber-300'
    case 'approved': return 'bg-emerald-100 text-emerald-900 border border-emerald-300'
    case 'rejected': return 'bg-red-100 text-red-900 border border-red-300'
    default: return 'bg-slate-100 text-slate-800'
  }
}

onMounted(() => {
  fetchApprovals()
})
</script>
