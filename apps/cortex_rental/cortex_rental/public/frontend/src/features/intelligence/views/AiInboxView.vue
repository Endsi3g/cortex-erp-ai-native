<template>
  <section class="mx-auto max-w-[1600px] space-y-4" data-test="screen-ai-inbox">
    <header class="flex flex-wrap items-end justify-between gap-3 border-b border-cortex-border pb-4">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-semibold">AI Inbox</h1>
          <Badge theme="green" variant="subtle">{{ pendingCount }} à traiter</Badge>
        </div>
        <p class="mt-1 text-xs text-cortex-text-secondary">Suggestions, demandes d’approbation et documents entrants réunis au même endroit.</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-[11px] text-cortex-text-muted">Ma boîte · entreprise active</span>
        <Button size="sm" variant="subtle" :loading="loading" @click="loadItems">Actualiser</Button>
      </div>
    </header>

    <div class="grid grid-cols-2 gap-2 md:grid-cols-4">
      <TabButtons v-model="activeType" :buttons="typeButtons" aria-label="Type de travail à afficher" />
    </div>

    <div class="flex flex-wrap items-center gap-2 rounded-md border border-cortex-border bg-white p-2.5">
      <TextInput v-model="search" class="min-w-48 flex-1" size="sm" variant="outline" aria-label="Rechercher dans l’inbox" placeholder="Client, suggestion ou agent…" />
      <Select v-model="confidenceFilter" class="min-w-40" size="sm" variant="outline" aria-label="Filtrer par confiance" :options="confidenceOptions" />
      <Select v-model="priorityFilter" class="min-w-36" size="sm" variant="outline" aria-label="Filtrer par priorité" :options="priorityOptions" />
      <TextInput v-model="dateFilter" type="date" class="min-w-36" size="sm" variant="outline" aria-label="Filtrer par date" />
    </div>

    <div v-if="error" class="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-900" role="alert">{{ error }}</div>
    <div v-if="bulkApprovals.length" class="flex items-center justify-between rounded-md border border-cortex-primary-200 bg-cortex-primary-50 px-3 py-2 text-xs">
      <span>{{ selectedIds.size }} élément(s) sélectionné(s)</span>
          <Button size="sm" variant="solid" theme="green" @click="requestBulkApproval">Valider {{ bulkApprovals.length }} approbation(s)</Button>
    </div>

    <div class="grid min-h-[560px] grid-cols-1 overflow-hidden rounded-md border border-cortex-border bg-white lg:grid-cols-[minmax(0,1fr)_390px]">
      <div class="min-w-0 overflow-x-auto">
        <table class="w-full border-collapse text-left text-xs">
          <thead class="sticky top-0 bg-cortex-surface-subtle text-[10px] uppercase tracking-wide text-cortex-text-secondary">
            <tr><th class="w-9 px-3 py-2"><Checkbox :model-value="allVisibleSelected" aria-label="Sélectionner les éléments visibles" @update:model-value="toggleVisible" /></th><th class="px-3 py-2">Suggestion</th><th class="px-3 py-2">Client / Référence</th><th class="px-3 py-2">Agent</th><th class="px-3 py-2">Confiance</th><th class="px-3 py-2">État</th><th class="px-3 py-2">Date</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredItems" :key="item.id" tabindex="0" class="cursor-pointer border-t border-cortex-border/70 hover:bg-cortex-surface-subtle/70 focus:bg-cortex-primary-50" :class="selected?.id === item.id ? 'bg-cortex-primary-50' : ''" @click="select(item)" @keydown.enter="select(item)" @keydown.space.prevent="select(item)">
              <td class="px-3 py-2.5" @click.stop><Checkbox :model-value="selectedIds.has(item.id)" :aria-label="`Sélectionner ${item.title}`" @update:model-value="onSelection(item.id, $event)" /></td>
              <td class="max-w-[300px] px-3 py-2.5"><div class="truncate font-medium text-cortex-text-primary">{{ item.title }}</div><div class="mt-0.5 text-[10px] text-cortex-text-muted">{{ typeLabels[item.type] }} · {{ item.summary }}</div></td>
              <td class="max-w-40 truncate px-3 py-2.5">{{ item.customer }}</td>
              <td class="whitespace-nowrap px-3 py-2.5">{{ item.agent }}</td>
              <td class="whitespace-nowrap px-3 py-2.5"><span class="font-mono" :class="item.confidence === null ? 'text-cortex-text-muted' : confidenceTone(item.confidence)">{{ item.confidence === null ? '—' : `${Math.round(item.confidence * 100)}%` }}</span></td>
              <td class="whitespace-nowrap px-3 py-2.5"><Badge :theme="stateTheme(item.state)" variant="subtle">{{ aiStateLabels[item.state] }}</Badge></td>
              <td class="whitespace-nowrap px-3 py-2.5 text-cortex-text-muted">{{ formatDate(item.createdAt) }}</td>
            </tr>
            <tr v-if="!loading && filteredItems.length === 0"><td colspan="7" class="px-5 py-16 text-center text-sm text-cortex-text-muted">Aucun élément ne correspond à ces filtres.</td></tr>
            <tr v-if="loading"><td colspan="7" class="px-5 py-16 text-center text-xs text-cortex-text-muted">Chargement des éléments IA…</td></tr>
          </tbody>
        </table>
      </div>

      <aside class="border-t border-cortex-border bg-[#fbfdfb] p-4 lg:border-l lg:border-t-0" aria-label="Détail de la suggestion">
        <template v-if="selected">
          <div class="flex items-start justify-between gap-3">
            <div><p class="text-[10px] font-semibold uppercase tracking-wider text-cortex-primary-700">{{ typeLabels[selected.type] }}</p><h2 class="mt-1 text-sm font-semibold leading-5">{{ selected.title }}</h2></div>
            <Button size="sm" variant="ghost" icon="x" aria-label="Fermer le détail" @click="selected = null" />
          </div>
          <p class="mt-3 text-xs leading-5 text-cortex-text-secondary">{{ selected.summary }}</p>
          <dl class="mt-4 grid grid-cols-2 gap-x-3 gap-y-3 border-y border-cortex-border py-3 text-xs">
            <div><dt class="text-[10px] text-cortex-text-muted">Confiance</dt><dd class="mt-1 font-semibold" :class="selected.confidence === null ? 'text-cortex-text-muted' : confidenceTone(selected.confidence)">{{ selected.confidence === null ? 'Non évaluée' : `${Math.round(selected.confidence * 100)}%` }}</dd></div>
            <div><dt class="text-[10px] text-cortex-text-muted">Priorité</dt><dd class="mt-1 capitalize">{{ priorityLabels[selected.priority] }}</dd></div>
            <div><dt class="text-[10px] text-cortex-text-muted">Agent</dt><dd class="mt-1">{{ selected.agent }}</dd></div>
          </dl>
          <div v-if="selected.type === 'inbound'" class="mt-4 space-y-2">
            <h3 class="text-xs font-semibold">Éléments extraits</h3>
            <p class="text-xs"><span class="text-cortex-text-muted">Client :</span> {{ (selected.source as InboundRequestItem).extracted_fields.customer_name || 'À préciser' }}</p>
            <p class="text-xs"><span class="text-cortex-text-muted">Période :</span> {{ dateRange(selected.source as InboundRequestItem) }}</p>
            <ul class="space-y-1 text-xs"><li v-for="gear in (selected.source as InboundRequestItem).extracted_fields.equipment_mentions || []" :key="gear.raw_text" class="flex justify-between gap-2"><span>{{ gear.quantity || 1 }} × {{ gear.raw_text }}</span><span :class="confidenceTone(gear.confidence)">{{ Math.round(gear.confidence * 100) }}%</span></li></ul>
            <p v-if="(selected.source as InboundRequestItem).extracted_fields.missing_fields.length" class="rounded bg-amber-50 p-2 text-xs text-amber-900">À compléter : {{ (selected.source as InboundRequestItem).extracted_fields.missing_fields.join(', ') }}</p>
          </div>
          <div v-if="selected.type === 'approval'" class="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">Cette action attend une personne ayant le rôle approprié. La règle serveur reste l’autorité pour l’approbation.</div>
          <div class="mt-5 flex flex-wrap gap-2">
            <Button size="sm" variant="solid" theme="green" @click="openWorkspace(selected)">Ouvrir / réviser</Button>
            <Button v-if="selected.type === 'approval' && canApprove" size="sm" variant="subtle" @click="approveOne(selected)">Valider</Button>
            <Button v-if="selected.type === 'inbound'" size="sm" variant="subtle" @click="openComposer(selected)">Ouvrir le Composer</Button>
          </div>
        </template>
        <div v-else class="flex h-full min-h-48 flex-col items-center justify-center text-center"><Sparkles class="h-6 w-6 text-cortex-primary-600" /><p class="mt-2 text-xs font-medium">Sélectionne un élément</p><p class="mt-1 max-w-56 text-[11px] text-cortex-text-muted">Le contexte, les preuves et les actions apparaîtront ici.</p></div>
      </aside>
    </div>
  </section>
  <Dialog v-model="approvalDialogOpen" :options="{ title: 'Confirmer les approbations', size: 'md' }" :disable-outside-click-to-close="approvalLoading">
    <template #body-content><p class="text-sm text-ink-gray-7">{{ confirmationMessage }} Chaque décision sera autorisée et journalisée côté serveur.</p></template>
    <template #actions="{ close }"><div class="flex justify-end gap-2"><Button variant="subtle" :disabled="approvalLoading" @click="close">Annuler</Button><Button theme="green" variant="solid" :loading="approvalLoading" @click="confirmApproval(close)">Confirmer</Button></div></template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Badge, Button, Checkbox, Dialog, Select, TabButtons, TextInput } from 'frappe-ui'
import { Sparkles } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { InboundRequestItem } from '@/api/contracts'
import { useSessionStore } from '@/stores/session'
import { aiStateLabels, toAiWorkItem, type AiWorkItem, type AiWorkType } from '../aiNative'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const items = ref<AiWorkItem[]>([])
const selected = ref<AiWorkItem | null>(null)
const selectedIds = ref(new Set<string>())
const approvalDialogOpen = ref(false)
const approvalLoading = ref(false)
const confirmationMessage = ref('')
const approvalTargets = ref<AiWorkItem[]>([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const activeType = ref<'all' | AiWorkType>((route.query.type as AiWorkType) || 'all')
const confidenceFilter = ref('all')
const priorityFilter = ref('all')
const dateFilter = ref('')
const tabs: Array<{ value: 'all' | AiWorkType; label: string }> = [
  { value: 'all', label: 'Tout' }, { value: 'inbound', label: 'Documents entrants' }, { value: 'draft', label: 'Suggestions & brouillons' }, { value: 'approval', label: 'Approbations' }
]
const typeButtons = computed(() => tabs.map(tab => ({ label: `${tab.label} (${countByType(tab.value)})`, value: tab.value, theme: 'gray' as const, variant: 'subtle' as const })))
const confidenceOptions = [
  { label: 'Toute confiance', value: 'all' }, { label: 'Confiance faible', value: 'low' },
  { label: 'Confiance moyenne', value: 'medium' }, { label: 'Confiance élevée', value: 'high' }
]
const priorityOptions = [
  { label: 'Toute priorité', value: 'all' }, { label: 'Urgente', value: 'urgent' },
  { label: 'Élevée', value: 'high' }, { label: 'Normale', value: 'normal' }, { label: 'Faible', value: 'low' }
]
const typeLabels: Record<AiWorkType, string> = { inbound: 'Document entrant', draft: 'Suggestion IA', approval: 'Approbation' }
const priorityLabels = { low: 'faible', normal: 'normale', high: 'élevée', urgent: 'urgente' }
const canApprove = computed(() => session.hasPermission('cortex:approvals:decide'))
const pendingCount = computed(() => items.value.filter(item => ['needs_review', 'ready', 'low_confidence', 'processing'].includes(item.state)).length)
const filteredItems = computed(() => items.value.filter(item => {
  if (activeType.value !== 'all' && item.type !== activeType.value) return false
  if (confidenceFilter.value !== 'all' && item.confidence === null) return false
  if (confidenceFilter.value === 'low' && item.confidence! >= 0.7) return false
  if (confidenceFilter.value === 'medium' && (item.confidence! < 0.7 || item.confidence! >= 0.9)) return false
  if (confidenceFilter.value === 'high' && item.confidence! < 0.9) return false
  if (priorityFilter.value !== 'all' && item.priority !== priorityFilter.value) return false
  if (dateFilter.value && !item.createdAt.startsWith(dateFilter.value)) return false
  const needle = search.value.trim().toLocaleLowerCase()
  return !needle || `${item.title} ${item.customer} ${item.agent} ${item.summary}`.toLocaleLowerCase().includes(needle)
}))
const allVisibleSelected = computed(() => filteredItems.value.length > 0 && filteredItems.value.every(item => selectedIds.value.has(item.id)))
const bulkApprovals = computed(() => items.value.filter(item => selectedIds.value.has(item.id) && item.type === 'approval' && item.state === 'needs_review'))

async function loadItems() {
  loading.value = true
  error.value = ''
  try {
    const api = getCortexApiClient()
    const [inbound, drafts, approvals] = await Promise.all([
      api.listInboundRequests({ page: 1, page_size: 100 }),
      api.listAiDrafts({ page: 1, page_size: 100 }),
      api.listApprovalRequests({ page: 1, page_size: 100, status: undefined })
    ])
    items.value = [
      ...inbound.items.map(item => toAiWorkItem(item, 'inbound')),
      ...drafts.items.map(item => toAiWorkItem(item, 'draft')),
      ...approvals.items.map(item => toAiWorkItem(item, 'approval'))
    ].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    const requestedId = route.params.itemId || route.query.item
    if (requestedId) selected.value = items.value.find(item => item.id === requestedId || item.sourceId === requestedId) || items.value[0] || null
    else if (!selected.value) selected.value = items.value.find(item => ['needs_review', 'low_confidence', 'ready'].includes(item.state)) || null
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Impossible de charger AI Inbox.'
  } finally {
    loading.value = false
  }
}

function countByType(type: 'all' | AiWorkType) { return type === 'all' ? items.value.length : items.value.filter(item => item.type === type).length }
function select(item: AiWorkItem) { selected.value = item }
function onSelection(id: string, checked: boolean) {
  const next = new Set(selectedIds.value)
  checked ? next.add(id) : next.delete(id)
  selectedIds.value = next
}
function toggleVisible(checked: boolean) {
  const next = new Set(selectedIds.value)
  for (const item of filteredItems.value) checked ? next.add(item.id) : next.delete(item.id)
  selectedIds.value = next
}
async function approveOne(item: AiWorkItem) {
  if (item.type !== 'approval' || !canApprove) return
  approvalTargets.value = [item]
  confirmationMessage.value = `Vous allez approuver « ${item.title} ».`
  approvalDialogOpen.value = true
}
function requestBulkApproval() {
  if (!canApprove || !bulkApprovals.value.length) return
  approvalTargets.value = [...bulkApprovals.value]
  confirmationMessage.value = `Vous allez approuver ${approvalTargets.value.length} demandes sélectionnées.`
  approvalDialogOpen.value = true
}
async function confirmApproval(close: () => void) {
  if (!canApprove || approvalLoading.value || !approvalTargets.value.length) return
  approvalLoading.value = true
  const failed: Array<{ item: AiWorkItem; message: string }> = []
  try {
    for (const item of approvalTargets.value) {
      try { await getCortexApiClient().approveApprovalRequest({ id: item.sourceId }) }
      catch (cause) { failed.push({ item, message: cause instanceof Error ? cause.message : 'Refus du serveur' }) }
    }
    selectedIds.value = new Set(failed.map(result => result.item.id))
    approvalDialogOpen.value = false
    close()
    await loadItems()
    if (failed.length) error.value = `Approbations refusées (${failed.length}) : ${failed.map(result => `${result.item.sourceId} — ${result.message}`).join('; ')}`
  } finally {
    approvalLoading.value = false
    approvalTargets.value = []
  }
}
function openWorkspace(item: AiWorkItem) { router.push({ name: 'ai-workspace', params: { itemId: item.id } }) }
function openComposer(item: AiWorkItem) { router.push({ name: 'rental-composer', query: { intake_id: item.sourceId } }) }
function formatDate(value: string) { return new Intl.DateTimeFormat(session.locale, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) }
function confidenceTone(value: number | null) { return value === null ? 'text-cortex-text-muted' : value < 0.7 ? 'text-red-700 font-semibold' : value < 0.9 ? 'text-amber-700' : 'text-cortex-primary-700' }
function stateTheme(state: AiWorkItem['state']) { return state === 'low_confidence' || state === 'extraction_error' ? 'red' : state === 'needs_review' ? 'orange' : ['validated', 'applied'].includes(state) ? 'green' : 'gray' }
function dateRange(item: InboundRequestItem) { const start = item.extracted_fields.start_date; const end = item.extracted_fields.end_date; return start && end ? `${formatDate(start)} – ${formatDate(end)}` : 'À confirmer' }
watch(() => route.query.type, value => { activeType.value = (value as AiWorkType) || 'all' })
onMounted(loadItems)
</script>
