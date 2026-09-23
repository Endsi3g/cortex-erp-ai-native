<template>
  <section class="mx-auto max-w-[1600px] space-y-4" data-test="screen-ai-workspace">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b border-cortex-border pb-3">
      <div class="flex min-w-0 items-center gap-3">
        <Button size="sm" variant="subtle" @click="router.push({ name: 'ai-inbox' })">← Inbox</Button>
        <div class="min-w-0"><h1 class="truncate text-lg font-semibold">AI Workspace</h1><p class="truncate text-xs text-cortex-text-muted">{{ item?.title || 'Document entrant et révision assistée' }}</p></div>
      </div>
      <div class="flex items-center gap-2">
        <Badge :theme="item && item.confidence !== null && item.confidence < 0.7 ? 'red' : 'green'" variant="subtle">{{ item?.confidence == null ? 'Confiance non évaluée' : `Confiance ${Math.round(item.confidence * 100)}%` }}</Badge>
        <Button size="sm" variant="subtle" @click="toggleDense">{{ dense ? 'Vue détaillée' : 'Vue compacte' }}</Button>
        <Button size="sm" variant="solid" theme="green" :disabled="!item || item.type !== 'inbound'" @click="openComposer">Ouvrir dans le Composer</Button>
      </div>
    </header>

    <div v-if="error" class="rounded border border-red-200 bg-red-50 p-3 text-xs text-red-900" role="alert">{{ error }}</div>
    <div v-if="item?.confidence !== null && item?.confidence !== undefined && item.confidence < 0.7" class="flex items-start gap-2 rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950" role="alert">
      <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" /><div><strong>Confiance faible : correction humaine requise.</strong><p class="mt-1">Les champs incertains sont signalés. La validation restera bloquée tant que les informations critiques ne sont pas vérifiées.</p></div>
    </div>

    <div class="grid min-h-[calc(100vh-210px)] grid-cols-1 gap-3 xl:grid-cols-2">
      <!-- Source document -->
      <section class="flex min-h-[560px] min-w-0 flex-col overflow-hidden rounded-md border border-cortex-border bg-white" aria-label="Document source">
        <header class="flex items-center justify-between border-b border-cortex-border bg-cortex-surface-subtle/60 px-4 py-3">
          <div class="flex items-center gap-2"><FileText class="h-4 w-4 text-cortex-text-secondary" /><h2 class="text-xs font-semibold">Source & preuves</h2></div>
          <span class="text-[10px] text-cortex-text-muted">{{ sourceLabel }}</span>
        </header>
        <div class="flex-1 overflow-auto p-4" :class="dense ? 'space-y-3' : 'space-y-5'">
          <template v-if="inbound">
            <div class="rounded border border-cortex-border bg-[#fafbfa] p-3 text-xs">
              <div class="grid grid-cols-[58px_1fr] gap-x-2 gap-y-1"><span class="text-cortex-text-muted">De</span><span>{{ inbound.sender_name || inbound.sender_email }} &lt;{{ inbound.sender_email }}&gt;</span><span class="text-cortex-text-muted">Objet</span><span class="font-medium">{{ inbound.subject }}</span><span class="text-cortex-text-muted">Reçu</span><span>{{ formatDate(inbound.received_at) }}</span></div>
            </div>
            <article class="whitespace-pre-wrap rounded border border-cortex-border/70 p-4 text-xs leading-6 text-cortex-text-secondary">{{ inbound.raw_body }}</article>
            <div v-if="inbound.source === 'pdf'" class="rounded border border-dashed border-cortex-border bg-cortex-surface-subtle/50 p-5 text-center text-xs text-cortex-text-muted"><FileText class="mx-auto mb-2 h-5 w-5" />Le fichier PDF original n’est pas encore fourni par l’API. Le texte extrait est affiché ci-dessus lorsque disponible.</div>
            <section class="rounded border border-cortex-border p-3">
              <div class="mb-2 flex items-center justify-between"><h3 class="text-xs font-semibold">Extraits de preuve</h3><Button size="xs" variant="subtle" :loading="extractingField !== ''" @click="requestFieldReview('all')">Réextraire le document</Button></div>
              <blockquote class="border-l-2 border-cortex-primary-500 pl-3 text-xs italic leading-5 text-cortex-text-secondary">{{ evidenceExcerpt }}</blockquote>
              <p class="mt-2 text-[10px] text-cortex-text-muted">Source : {{ inbound.source }} · SHA-256 : <span class="font-mono">Non fourni par le contrat d’ingestion actuel</span></p>
            </section>
          </template>
          <template v-else-if="draft">
            <div class="rounded border border-cortex-border p-4"><h3 class="text-sm font-semibold">{{ draft.title }}</h3><p class="mt-2 text-xs text-cortex-text-secondary">Type : {{ draft.draft_type }} · Cible : {{ draft.target_doctype }} {{ draft.target_name || '' }}</p><pre class="mt-3 max-h-96 overflow-auto rounded bg-cortex-surface-subtle p-3 text-[11px] leading-5">{{ JSON.stringify(draft.proposed_payload, null, 2) }}</pre></div>
            <div class="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">La preuve liée au brouillon doit être chargée depuis le service Evidence pour afficher le document original et ses empreintes.</div>
          </template>
          <div v-else-if="loading" class="py-20 text-center text-xs text-cortex-text-muted">Chargement du document…</div>
          <div v-else class="py-20 text-center text-xs text-cortex-text-muted">Aucun document lié. Ouvre un élément depuis AI Inbox.</div>
        </div>
      </section>

      <!-- Editable extraction, diff, contextual conversation -->
      <section class="flex min-h-[560px] min-w-0 flex-col overflow-hidden rounded-md border border-cortex-border bg-white" aria-label="Brouillon et assistant">
        <div class="flex border-b border-cortex-border">
          <TabButtons v-model="activeTab" class="p-1" :buttons="workspaceTabButtons" aria-label="Vue du workspace" />
        </div>
        <div v-if="activeTab === 'draft'" class="flex-1 space-y-4 overflow-auto p-4">
          <div class="flex items-start justify-between gap-3"><div><h2 class="text-sm font-semibold">Données structurées</h2><p class="mt-1 text-[11px] text-cortex-text-muted">Les corrections restent locales à cette session jusqu’à leur enregistrement par une API métier.</p></div><Badge theme="gray" variant="subtle">{{ edited ? 'Modifié par vous' : 'Brouillon IA' }}</Badge></div>
          <label class="block space-y-1 text-xs"><span class="text-cortex-text-muted">Client</span><TextInput v-model="fields.customer" size="sm" variant="outline" :class="editedField('customer')" @update:model-value="markEdited('customer')" /></label>
          <div class="grid grid-cols-2 gap-3"><label class="space-y-1 text-xs"><span class="text-cortex-text-muted">Début</span><TextInput v-model="fields.start" type="datetime-local" size="sm" variant="outline" :class="editedField('start')" @update:model-value="markEdited('start')" /></label><label class="space-y-1 text-xs"><span class="text-cortex-text-muted">Fin</span><TextInput v-model="fields.end" type="datetime-local" size="sm" variant="outline" :class="editedField('end')" @update:model-value="markEdited('end')" /></label></div>
          <div><div class="mb-2 flex items-center justify-between"><h3 class="text-xs font-semibold">Équipement demandé</h3><Button size="xs" variant="subtle" @click="requestFieldReview('equipment')">Réextraire ce champ</Button></div><div v-for="(gear, index) in fields.gear" :key="index" class="mb-2 grid grid-cols-[1fr_70px_auto] gap-2"><TextInput v-model="gear.label" size="sm" variant="outline" :class="editedField(`gear-${index}`)" :aria-label="`Équipement ${index + 1}`" @update:model-value="markEdited(`gear-${index}`)" /><TextInput v-model.number="gear.quantity" type="number" min="1" size="sm" variant="outline" :class="editedField(`gear-${index}`)" :aria-label="`Quantité équipement ${index + 1}`" @update:model-value="markEdited(`gear-${index}`)" /><Button size="xs" variant="subtle" @click="requestFieldReview(`gear-${index}`)">Réextraire</Button></div></div>
          <section class="rounded border border-cortex-border"><div class="border-b border-cortex-border px-3 py-2 text-xs font-semibold">Comparaison avec la source</div><div class="grid grid-cols-2 divide-x divide-cortex-border text-xs"><div class="p-3"><p class="mb-2 text-[10px] uppercase text-cortex-text-muted">Extrait</p><p>{{ inbound?.extracted_fields.customer_name || '—' }}</p><p class="mt-2">{{ inbound?.extracted_fields.start_date || '—' }}</p><p class="mt-2">{{ inbound?.extracted_fields.end_date || '—' }}</p></div><div class="p-3"><p class="mb-2 text-[10px] uppercase text-cortex-text-muted">Valeur actuelle</p><p :class="editedField('customer')">{{ fields.customer || '—' }}</p><p class="mt-2" :class="editedField('start')">{{ fields.start || '—' }}</p><p class="mt-2" :class="editedField('end')">{{ fields.end || '—' }}</p></div></div></section>
          <p v-if="notice" class="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900" role="status">{{ notice }}</p>
          <div class="flex flex-wrap gap-2 border-t border-cortex-border pt-3"><Button size="sm" variant="subtle" :disabled="!edited" @click="restoreOriginal">Restaurer la version chargée</Button><Button size="sm" variant="solid" theme="green" @click="openComposer">Continuer dans le Composer</Button><Button v-if="approval" size="sm" variant="subtle" @click="openApproval">Voir l’approbation</Button></div>
        </div>
        <div v-else-if="activeTab === 'chat'" class="flex min-h-0 flex-1 flex-col">
          <div ref="chatLog" class="flex-1 space-y-3 overflow-auto p-4" role="log" aria-live="polite">
            <div v-if="!messages.length" class="rounded bg-cortex-surface-subtle/60 p-3 text-xs text-cortex-text-secondary">Discute avec l’agent en gardant le document et les données extraites comme contexte.</div>
            <article v-for="message in messages" :key="message.id" class="max-w-[92%] rounded-md border p-3 text-xs leading-5" :class="message.sender === 'user' ? 'ml-auto border-cortex-primary-200 bg-cortex-primary-50' : 'border-cortex-border bg-white'"><p class="mb-1 text-[10px] font-semibold text-cortex-text-muted">{{ message.sender === 'user' ? 'Vous' : agentLabel }}</p><p class="whitespace-pre-wrap">{{ message.content }}</p><div v-if="message.evidence_refs?.length" class="mt-2 border-t border-cortex-border pt-2 text-[10px]">Preuves : {{ message.evidence_refs.map(ref => ref.name).join(', ') }}</div></article>
            <p v-if="chatError" class="text-xs text-red-700" role="alert">{{ chatError }}</p>
          </div>
          <form class="flex items-end gap-2 border-t border-cortex-border p-3" @submit.prevent="sendMessage"><Input type="textarea" :model-value="prompt" class="min-h-10 flex-1" input-class="resize-y text-xs" :rows="2" placeholder="Demande une analyse de ce document…" :disabled="sending" aria-label="Message à l’assistant" @input="prompt = $event" /><Button type="submit" size="sm" variant="solid" theme="green" :loading="sending" :disabled="!prompt.trim()">Envoyer</Button></form>
          <p class="border-t border-cortex-border bg-cortex-surface-subtle px-3 py-2 text-[10px] text-cortex-text-muted">{{ provenance === 'frappe-onyx' ? 'Réponse fournie par Onyx via la passerelle Frappe. Les réponses du modèle restent des suggestions; les faits métier doivent être vérifiés par les services ERP.' : 'Les messages sont envoyés à la passerelle Frappe authentifiée. Le modèle et ses outils sont configurés côté serveur.' }}</p>
        </div>
        <div v-else class="flex-1 space-y-3 overflow-auto p-4"><h2 class="text-sm font-semibold">Historique des versions</h2><p class="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">Le contrat d’API actuel ne fournit pas encore de versionnement/restauration du brouillon. La version initiale est conservée en mémoire jusqu’à fermeture de cette page.</p><div class="rounded border border-cortex-border p-3 text-xs"><span class="font-medium">Version chargée</span><span class="float-right text-cortex-text-muted">{{ item ? formatDate(item.createdAt) : '—' }}</span></div></div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Badge, Button, Input, TabButtons, TextInput } from 'frappe-ui'
import { FileText, TriangleAlert } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { AiDraftItem, ApprovalRequestItem, CopilotMessage, InboundRequestItem } from '@/api/contracts'
import { useSessionStore } from '@/stores/session'
import { toAiWorkItem, type AiWorkItem } from '../aiNative'
import { createAiChatSession, sendAiChatMessage } from '../aiChatGateway'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const loading = ref(true)
const error = ref('')
const notice = ref('')
const inbound = ref<InboundRequestItem | null>(null)
const draft = ref<AiDraftItem | null>(null)
const approval = ref<ApprovalRequestItem | null>(null)
const item = ref<AiWorkItem | null>(null)
const fields = reactive({ customer: '', start: '', end: '', gear: [] as Array<{ label: string; quantity: number }> })
const original = ref('')
const editedKeys = ref(new Set<string>())
const extractingField = ref('')
const activeTab = ref<'draft' | 'chat' | 'history'>('draft')
const rightTabs = [{ key: 'draft', label: 'Brouillon' }, { key: 'chat', label: 'Conversation' }, { key: 'history', label: 'Versions' }] as const
const workspaceTabButtons = rightTabs.map(tab => ({ label: tab.label, value: tab.key, theme: 'gray' as const, variant: 'subtle' as const }))
const dense = ref(false)
const prompt = ref('')
const sending = ref(false)
const chatError = ref('')
const messages = ref<CopilotMessage[]>([])
const sessionId = ref('')
const provenance = ref('')
const chatLog = ref<HTMLElement | null>(null)
const agentLabel = computed(() => item.value?.agent || 'Assistant location')
const edited = computed(() => editedKeys.value.size > 0)
const sourceLabel = computed(() => inbound.value?.source === 'email' ? 'Courriel' : inbound.value?.source === 'pdf' ? 'PDF' : draft.value ? 'Brouillon structuré' : 'Source métier')
const evidenceExcerpt = computed(() => inbound.value?.raw_body.trim().split(/\s+/).slice(0, 38).join(' ') || 'Aucun extrait de preuve disponible.')

async function loadWorkspace() {
  loading.value = true
  try {
    const id = String(route.params.itemId || '')
    const [inboundRes, draftsRes, approvalsRes] = await Promise.all([
      getCortexApiClient().listInboundRequests({ page: 1, page_size: 100 }),
      getCortexApiClient().listAiDrafts({ page: 1, page_size: 100 }),
      getCortexApiClient().listApprovalRequests({ page: 1, page_size: 100, status: undefined })
    ])
    const [kind, sourceId] = id.includes(':') ? id.split(':', 2) : ['', id]
    inbound.value = kind === 'inbound' ? inboundRes.items.find(row => row.id === sourceId) || null : null
    draft.value = kind === 'draft' ? draftsRes.items.find(row => row.id === sourceId) || null : null
    approval.value = kind === 'approval' ? approvalsRes.items.find(row => row.id === sourceId) || null : null
    const selectedSource = inbound.value || draft.value || approval.value
    item.value = selectedSource ? toAiWorkItem(selectedSource, kind as 'inbound' | 'draft' | 'approval') : null
    if (inbound.value) {
      const extracted = inbound.value.extracted_fields
      fields.customer = extracted.customer_name || ''
      fields.start = toLocalDate(extracted.start_date)
      fields.end = toLocalDate(extracted.end_date)
      fields.gear = (extracted.equipment_mentions || []).map(gear => ({ label: gear.raw_text, quantity: gear.quantity || 1 }))
    }
    original.value = JSON.stringify(fields)
  } catch (cause) { error.value = cause instanceof Error ? cause.message : 'Impossible de charger le workspace.' }
  finally { loading.value = false }
}
function toLocalDate(value?: string) { if (!value) return ''; const date = new Date(value); return Number.isNaN(date.getTime()) ? '' : new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16) }
function markEdited(key: string) { editedKeys.value = new Set(editedKeys.value).add(key) }
function editedField(key: string) { return editedKeys.value.has(key) ? 'border-cortex-primary-500 bg-cortex-primary-50/40' : '' }
function toggleDense() { dense.value = !dense.value }
function restoreOriginal() { Object.assign(fields, JSON.parse(original.value)); editedKeys.value = new Set(); notice.value = 'La version initiale chargée a été restaurée.' }
function formatDate(value: string) { return new Intl.DateTimeFormat(session.locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
function openComposer() { if (!inbound.value) return; router.push({ name: 'rental-composer', query: { intake_id: inbound.value.id, customer: fields.customer, starts_at: fields.start, ends_at: fields.end } }) }
function openApproval() { if (approval.value) router.push({ name: 'approval-queue' }) }
async function requestFieldReview(field: string) {
  extractingField.value = field
  notice.value = 'La réextraction ciblée sera disponible lorsque l’API Intake/Onyx exposera cette action. Aucune valeur n’a été remplacée.'
  window.setTimeout(() => { extractingField.value = '' }, 250)
}
async function sendMessage() {
  if (!prompt.value.trim() || sending.value) return
  sending.value = true; chatError.value = ''
  try {
    if (!sessionId.value) {
      const page = inbound.value ? 'inbound' : draft.value ? 'transaction' : 'approvals'
      sessionId.value = await createAiChatSession(page, session.locale)
    }
    const content = prompt.value.trim(); prompt.value = ''
    const response = await sendAiChatMessage(content, sessionId.value, {
      page: inbound.value ? 'inbound' : draft.value ? 'transaction' : 'approvals',
      locale: session.locale,
      active_doctype: inbound.value ? 'Cortex Inbound Request' : draft.value ? 'Cortex AI Draft' : approval.value ? 'Approval Request' : undefined,
      active_document_name: inbound.value?.id || draft.value?.id || approval.value?.id,
      active_filters: edited.value ? { unsaved_local_draft_edits: [...editedKeys.value] } : {}
    })
    provenance.value = 'frappe-onyx'
    messages.value = [...messages.value, response.userMessage, response.assistantMessage]
    await nextTick(); chatLog.value?.scrollTo({ top: chatLog.value.scrollHeight, behavior: 'smooth' })
  } catch (cause) { chatError.value = cause instanceof Error ? cause.message : 'L’assistant est temporairement indisponible.' }
  finally { sending.value = false }
}
onMounted(loadWorkspace)
</script>
