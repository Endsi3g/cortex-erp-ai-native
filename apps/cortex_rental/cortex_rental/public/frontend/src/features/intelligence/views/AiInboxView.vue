<template>
  <div class="cx-page" data-test="screen-ai-inbox">
    <CortexPageHeader title="AI Inbox" subtitle="Suggestions, demandes d’approbation et documents entrants, avec la source de chacune.">
      <template #actions>
        <span class="cx-tag cx-tag--ok">{{ pendingCount }} à traiter</span>
        <RefreshButton :loading="loading" @refresh="loadItems" />
      </template>
    </CortexPageHeader>

    <div class="cx-tabs" role="tablist" aria-label="Type de travail à afficher">
      <button v-for="tab in tabs" :key="tab.value" type="button" role="tab" class="cx-tab" :aria-selected="activeType === tab.value" @click="activeType = tab.value">
        {{ tab.label }} ({{ countByType(tab.value) }})
      </button>
    </div>

    <div class="cx-filters">
      <FilterField label="Rechercher dans l’inbox"><input v-model="search" type="search" class="cx-field" placeholder="Client, suggestion ou agent" /></FilterField>
      <FilterField label="Confiance"><select v-model="confidenceFilter" class="cx-field"><option v-for="o in confidenceOptions" :key="o.value" :value="o.value">{{ o.label }}</option></select></FilterField>
      <FilterField label="Priorité"><select v-model="priorityFilter" class="cx-field"><option v-for="o in priorityOptions" :key="o.value" :value="o.value">{{ o.label }}</option></select></FilterField>
      <FilterField label="Date"><input v-model="dateFilter" type="date" class="cx-field" /></FilterField>
    </div>

    <div v-if="error" class="cx-notice" role="alert">{{ error }}</div>
    <div v-for="notice in notices" :key="notice" class="cx-notice" role="status">{{ notice }}</div>

    <div v-if="bulkApprovals.length" class="cx-notice">
      <span>{{ selectedIds.size }} élément(s) sélectionné(s)</span>
      <button type="button" class="cx-btn-primary" @click="requestBulkApproval">Valider {{ bulkApprovals.length }} approbation(s)</button>
    </div>
    <div v-if="approvalDialogOpen" class="cx-notice" role="alertdialog" aria-label="Confirmer les approbations">
      <span>{{ confirmationMessage }} Chaque décision sera autorisée et journalisée côté serveur.</span>
      <span class="cx-actions">
        <button type="button" class="cx-btn-soft" :disabled="approvalLoading" @click="approvalDialogOpen = false">Annuler</button>
        <button type="button" class="cx-btn-primary" :disabled="approvalLoading" @click="confirmApproval">Confirmer</button>
      </span>
    </div>

    <div class="cx-split">
      <div class="cx-tablewrap">
        <table class="cx-table">
          <thead>
            <tr>
              <th scope="col" class="cx-rownum"><input type="checkbox" :checked="allVisibleSelected" aria-label="Sélectionner les éléments visibles" @change="toggleVisible(($event.target as HTMLInputElement).checked)" /></th>
              <th scope="col">Suggestion</th><th scope="col">Client / référence</th><th scope="col">Agent</th>
              <th scope="col" class="num">Confiance</th><th scope="col">État</th><th scope="col">Date</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredItems" :key="item.id" tabindex="0" class="cx-clickable" :aria-selected="selected?.id === item.id" @click="select(item)" @keydown.enter="select(item)" @keydown.space.prevent="select(item)">
              <td class="cx-rownum" @click.stop><input type="checkbox" :checked="selectedIds.has(item.id)" :aria-label="`Sélectionner ${item.title}`" @change="onSelection(item.id, ($event.target as HTMLInputElement).checked)" /></td>
              <td><div class="truncate-cell font-medium">{{ item.title }}</div><div style="font-size: 12px; color: var(--erp-muted)">{{ typeLabels[item.type] }} · {{ item.summary }}</div></td>
              <td class="truncate-cell">{{ item.customer }}</td>
              <td>{{ item.agent }}</td>
              <td class="num" :class="confidenceTone(item.confidence)">{{ item.confidence === null ? 'non évaluée' : `${Math.round(item.confidence * 100)} %` }}</td>
              <td><span class="cx-tag" :class="stateTag(item.state)">{{ aiStateLabels[item.state] }}</span></td>
              <td>{{ formatDate(item.createdAt) }}</td>
            </tr>
            <tr v-if="loading"><td colspan="7" class="cx-empty">Chargement des éléments IA…</td></tr>
            <tr v-else-if="filteredItems.length === 0"><td colspan="7" class="cx-empty"><strong>Aucun élément</strong>Aucun élément ne correspond à ces filtres.</td></tr>
          </tbody>
        </table>
      </div>

      <aside aria-label="Détail de la suggestion">
        <template v-if="selected">
          <div class="flex items-start justify-between gap-3">
            <div><p class="m-0 text-xs" style="color: var(--erp-muted)">{{ typeLabels[selected.type] }}</p><h2 class="m-0 mt-1 text-base font-semibold">{{ selected.title }}</h2></div>
            <button type="button" class="cx-btn-soft cx-btn-icon" aria-label="Fermer le détail" @click="selected = null">✕</button>
          </div>
          <p class="mt-3 text-sm">{{ selected.summary }}</p>
          <dl class="cx-dl mt-4">
            <div><dt>Confiance</dt><dd :class="confidenceTone(selected.confidence)">{{ selected.confidence === null ? 'Non évaluée' : `${Math.round(selected.confidence * 100)} %` }}</dd></div>
            <div><dt>Priorité</dt><dd>{{ priorityLabels[selected.priority] }}</dd></div>
            <div><dt>Agent</dt><dd>{{ selected.agent }}</dd></div>
          </dl>
          <div v-if="selected.type === 'inbound'" class="mt-4">
            <h3 class="m-0 mb-2 text-sm font-semibold">Éléments extraits</h3>
            <p class="m-0 text-sm"><span style="color: var(--erp-muted)">Client:</span> {{ (selected.source as InboundRequestItem).extracted_fields.customer_name || 'À préciser' }}</p>
            <p class="m-0 mt-1 text-sm"><span style="color: var(--erp-muted)">Période:</span> {{ dateRange(selected.source as InboundRequestItem) }}</p>
            <ul class="m-0 mt-2 list-none p-0 text-sm">
              <li v-for="gear in (selected.source as InboundRequestItem).extracted_fields.equipment_mentions || []" :key="gear.raw_text" class="flex justify-between gap-2 py-1">
                <span>{{ gear.quantity || 1 }} × {{ gear.raw_text }}</span>
                <span :class="confidenceTone(gear.confidence ?? null)">{{ gear.confidence == null ? 'non évaluée' : `${Math.round(gear.confidence * 100)} %` }}</span>
              </li>
            </ul>
            <p v-if="(selected.source as InboundRequestItem).extracted_fields.missing_fields.length" class="cx-notice" style="margin: 12px 0 0">À compléter: {{ (selected.source as InboundRequestItem).extracted_fields.missing_fields.join(', ') }}</p>
          </div>
          <p v-if="selected.type === 'approval'" class="cx-notice" style="margin: 16px 0 0">Cette action attend une personne ayant le rôle approprié. La règle serveur reste l’autorité pour l’approbation.</p>
          <div class="cx-actions mt-5">
            <button type="button" class="cx-btn-primary" @click="openWorkspace(selected)">Ouvrir / réviser</button>
            <button v-if="selected.type === 'approval' && canApprove" type="button" class="cx-btn-soft" @click="approveOne(selected)">Valider</button>
            <button v-if="selected.type === 'inbound'" type="button" class="cx-btn-soft" @click="openComposer(selected)">Ouvrir le composer</button>
          </div>
        </template>
        <div v-else class="cx-empty"><strong>Sélectionnez un élément</strong>Le contexte, les preuves et les actions apparaîtront ici.</div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCortexApiClient } from '@/api'
import type { InboundRequestItem } from '@/api/contracts'
import { useSessionStore } from '@/stores/session'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import FilterField from '@/features/common/components/FilterField.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
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
const notices = ref<string[]>([])
const search = ref('')
const activeType = ref<'all' | AiWorkType>((route.query.type as AiWorkType) || 'all')
const confidenceFilter = ref('all')
const priorityFilter = ref('all')
const dateFilter = ref('')
const tabs: Array<{ value: 'all' | AiWorkType; label: string }> = [
  { value: 'all', label: 'Tout' }, { value: 'inbound', label: 'Documents entrants' }, { value: 'draft', label: 'Suggestions & brouillons' }, { value: 'approval', label: 'Approbations' }
]
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
  notices.value = []
  try {
    const api = getCortexApiClient()
    // Each source has its own permission: a role that cannot read one still sees the others.
    const [inbound, drafts, approvals] = await Promise.allSettled([
      api.listInboundRequests({ page: 1, page_size: 100 }),
      api.listAiDrafts({ page: 1, page_size: 100 }),
      api.listApprovalRequests({ page: 1, page_size: 100, status: undefined })
    ])
    const problems: string[] = []
    const rows: AiWorkItem[] = []
    if (inbound.status === 'fulfilled') rows.push(...inbound.value.items.map(item => toAiWorkItem(item, 'inbound')))
    else problems.push(`Documents entrants: ${inbound.reason instanceof Error ? inbound.reason.message : 'indisponibles'}`)
    if (drafts.status === 'fulfilled') rows.push(...drafts.value.items.map(item => toAiWorkItem(item, 'draft')))
    else problems.push(`Suggestions: ${drafts.reason instanceof Error ? drafts.reason.message : 'indisponibles'}`)
    if (approvals.status === 'fulfilled') rows.push(...approvals.value.items.map(item => toAiWorkItem(item, 'approval')))
    else problems.push(`Approbations: ${approvals.reason instanceof Error ? approvals.reason.message : 'indisponibles'}`)
    if (problems.length === 3) error.value = problems.join(' · ')
    else if (problems.length) notices.value = problems
    items.value = rows.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
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
async function confirmApproval() {
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
function confidenceTone(value: number | null) { return value === null ? '' : value < 0.7 ? 'text-red-700 font-semibold' : value < 0.9 ? 'text-amber-700' : '' }
function stateTag(state: AiWorkItem['state']) { return state === 'low_confidence' || state === 'extraction_error' ? 'cx-tag--bad' : state === 'needs_review' ? 'cx-tag--warn' : ['validated', 'applied'].includes(state) ? 'cx-tag--ok' : '' }
function dateRange(item: InboundRequestItem) { const start = item.extracted_fields.start_date; const end = item.extracted_fields.end_date; return start && end ? `${formatDate(start)} – ${formatDate(end)}` : 'À confirmer' }
watch(() => route.query.type, value => { activeType.value = (value as AiWorkType) || 'all' })
onMounted(loadItems)
</script>
