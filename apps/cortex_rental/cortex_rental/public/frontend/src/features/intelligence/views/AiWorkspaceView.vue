<template>
  <div class="cx-page" data-test="screen-ai-workspace">
    <CortexPageHeader title="AI Workspace" :subtitle="item?.title || 'Document entrant et révision assistée'">
      <template #actions>
        <RouterLink to="/app/cortex-ai-inbox" class="cx-btn-soft">AI Inbox</RouterLink>
        <span class="cx-tag" :class="item && item.confidence !== null && item.confidence < 0.7 ? 'cx-tag--bad' : 'cx-tag--ok'">{{ item?.confidence == null ? 'Confiance non évaluée' : `Confiance ${Math.round(item.confidence * 100)} %` }}</span>
        <button type="button" class="cx-btn-soft" @click="toggleDense">{{ dense ? 'Vue détaillée' : 'Vue compacte' }}</button>
        <button type="button" class="cx-btn-primary" :disabled="!item || item.type !== 'inbound'" @click="openComposer">Ouvrir dans le composer</button>
      </template>
    </CortexPageHeader>

    <div v-if="error" class="cx-notice" role="alert">{{ error }}</div>
    <div v-if="item?.confidence !== null && item?.confidence !== undefined && item.confidence < 0.7" class="cx-notice" role="alert">
      <span><strong>Confiance faible: correction humaine requise.</strong> Les champs incertains sont signalés; la validation reste bloquée tant que les informations critiques ne sont pas vérifiées.</span>
    </div>

    <div class="cx-split" style="min-height: 560px">
      <section aria-label="Document source" class="min-w-0">
        <div class="cx-titlebar" style="min-height: 44px"><h2 class="m-0 text-sm font-semibold">Source et preuves</h2><span class="cx-tag">{{ sourceLabel }}</span></div>
        <div class="cx-section" :style="{ display: 'grid', gap: dense ? '12px' : '20px' }">
          <template v-if="inbound">
            <dl class="cx-dl">
              <div><dt>De</dt><dd>{{ inbound.sender_name || inbound.sender_email }} &lt;{{ inbound.sender_email }}&gt;</dd></div>
              <div><dt>Objet</dt><dd>{{ inbound.subject }}</dd></div>
              <div><dt>Reçu</dt><dd>{{ formatDate(inbound.received_at) }}</dd></div>
            </dl>
            <article class="whitespace-pre-wrap text-sm" style="padding: 16px; border: 1px solid var(--erp-border); border-radius: 8px; line-height: 1.7">{{ inbound.raw_body }}</article>
            <p v-if="inbound.source === 'pdf'" class="cx-notice" style="margin: 0">Le fichier PDF original n’est pas encore fourni par l’API. Le texte extrait est affiché ci-dessus lorsque disponible.</p>
            <section aria-label="Extraits de preuve">
              <div class="mb-2 flex items-center justify-between"><h3 class="m-0 text-sm font-semibold">Extrait de preuve</h3><button type="button" class="cx-btn-soft" :disabled="extractingField !== ''" @click="requestFieldReview('all')">Réextraire le document</button></div>
              <blockquote class="m-0 text-sm italic" style="border-left: 2px solid var(--erp-accent); padding-left: 12px; color: var(--erp-text-2)">{{ evidenceExcerpt }}</blockquote>
              <p class="mt-2 text-xs" style="color: var(--erp-muted)">Source: {{ inbound.source }} · SHA-256: non fourni par le contrat d’ingestion actuel</p>
            </section>
          </template>
          <template v-else-if="draft">
            <div>
              <h3 class="m-0 text-base font-semibold">{{ draft.title }}</h3>
              <p class="mt-1 text-sm" style="color: var(--erp-text-2)">Type: {{ draft.draft_type }} · Cible: {{ draft.target_doctype }} {{ draft.target_name || '' }}</p>
              <pre class="mt-3 max-h-96 overflow-auto text-xs" style="padding: 12px; background: var(--erp-field); border-radius: 8px">{{ JSON.stringify(draft.proposed_payload, null, 2) }}</pre>
            </div>
            <p class="cx-notice" style="margin: 0">La preuve liée au brouillon doit être chargée depuis le service Evidence pour afficher le document original et ses empreintes.</p>
          </template>
          <div v-else-if="loading" class="cx-empty">Chargement du document…</div>
          <div v-else class="cx-empty"><strong>Aucun document lié</strong>Ouvrez un élément depuis AI Inbox.</div>
        </div>
      </section>

      <aside aria-label="Brouillon et assistant" style="padding: 0">
        <div class="cx-tabs" role="tablist" aria-label="Vue du workspace">
          <button v-for="tab in rightTabs" :key="tab.key" type="button" role="tab" class="cx-tab" :aria-selected="activeTab === tab.key" @click="activeTab = tab.key">{{ tab.label }}</button>
        </div>

        <div v-if="activeTab === 'draft'" class="cx-section" style="display: grid; gap: 16px">
          <div class="flex items-start justify-between gap-3">
            <div><h2 class="m-0 text-base font-semibold">Données structurées</h2><p class="m-0 mt-1 text-xs" style="color: var(--erp-muted)">Les corrections restent locales à cette session jusqu’à leur enregistrement par une API métier.</p></div>
            <span class="cx-tag">{{ edited ? 'Modifié par vous' : 'Brouillon IA' }}</span>
          </div>
          <label class="block"><span class="mb-1 block text-xs" style="color: var(--erp-muted)">Client</span><input v-model="fields.customer" class="cx-field" :class="editedField('customer')" @input="markEdited('customer')" /></label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block"><span class="mb-1 block text-xs" style="color: var(--erp-muted)">Début</span><input v-model="fields.start" type="datetime-local" class="cx-field" :class="editedField('start')" @input="markEdited('start')" /></label>
            <label class="block"><span class="mb-1 block text-xs" style="color: var(--erp-muted)">Fin</span><input v-model="fields.end" type="datetime-local" class="cx-field" :class="editedField('end')" @input="markEdited('end')" /></label>
          </div>
          <div>
            <div class="mb-2 flex items-center justify-between"><h3 class="m-0 text-sm font-semibold">Équipement demandé</h3><button type="button" class="cx-btn-soft" @click="requestFieldReview('equipment')">Réextraire ce champ</button></div>
            <div v-for="(gear, index) in fields.gear" :key="index" class="mb-2 grid gap-2" style="grid-template-columns: 1fr 72px auto">
              <input v-model="gear.label" class="cx-field" :class="editedField(`gear-${index}`)" :aria-label="`Équipement ${index + 1}`" @input="markEdited(`gear-${index}`)" />
              <input v-model.number="gear.quantity" type="number" min="1" class="cx-field" :class="editedField(`gear-${index}`)" :aria-label="`Quantité équipement ${index + 1}`" @input="markEdited(`gear-${index}`)" />
              <button type="button" class="cx-btn-soft" @click="requestFieldReview(`gear-${index}`)">Réextraire</button>
            </div>
          </div>
          <div class="cx-tablewrap">
            <table class="cx-table" aria-label="Comparaison avec la source">
              <thead><tr><th scope="col">Champ</th><th scope="col">Extrait</th><th scope="col">Valeur actuelle</th></tr></thead>
              <tbody>
                <tr><td>Client</td><td>{{ inbound?.extracted_fields.customer_name || '—' }}</td><td :class="editedField('customer')">{{ fields.customer || '—' }}</td></tr>
                <tr><td>Début</td><td>{{ inbound?.extracted_fields.start_date || '—' }}</td><td :class="editedField('start')">{{ fields.start || '—' }}</td></tr>
                <tr><td>Fin</td><td>{{ inbound?.extracted_fields.end_date || '—' }}</td><td :class="editedField('end')">{{ fields.end || '—' }}</td></tr>
              </tbody>
            </table>
          </div>
          <p v-if="notice" class="cx-notice" style="margin: 0" role="status">{{ notice }}</p>
          <div class="cx-actions" style="padding-top: 8px; border-top: 1px solid var(--erp-border)">
            <button type="button" class="cx-btn-soft" :disabled="!edited" @click="restoreOriginal">Restaurer la version chargée</button>
            <button v-if="approval" type="button" class="cx-btn-soft" @click="openApproval">Voir l’approbation</button>
          </div>
        </div>

        <div v-else-if="activeTab === 'chat'" class="flex min-h-0 flex-col" style="min-height: 480px">
          <div ref="chatLog" class="cx-section flex-1 overflow-auto" style="display: grid; gap: 12px; align-content: start" role="log" aria-live="polite">
            <p v-if="!messages.length" class="cx-notice" style="margin: 0">Discutez avec l’agent en gardant le document et les données extraites comme contexte.</p>
            <article v-for="message in messages" :key="message.id" class="text-sm" :style="{ maxWidth: '92%', marginLeft: message.sender === 'user' ? 'auto' : '0', padding: '12px', border: '1px solid var(--erp-border)', borderRadius: '8px', background: message.sender === 'user' ? 'var(--erp-field)' : '#fff' }">
              <p class="m-0 mb-1 text-xs font-semibold" style="color: var(--erp-muted)">{{ message.sender === 'user' ? 'Vous' : agentLabel }}</p>
              <p class="m-0 whitespace-pre-wrap">{{ message.content }}</p>
              <p v-if="message.evidence_refs?.length" class="m-0 mt-2 text-xs" style="color: var(--erp-muted)">Preuves: {{ message.evidence_refs.map(ref => ref.name).join(', ') }}</p>
            </article>
            <p v-if="chatError" class="m-0 text-sm text-red-700" role="alert">{{ chatError }}</p>
          </div>
          <form class="flex items-end gap-2" style="padding: 12px 20px; border-top: 1px solid var(--erp-border)" @submit.prevent="sendMessage">
            <textarea v-model="prompt" class="cx-field flex-1" style="padding: 8px 12px; resize: vertical" rows="2" placeholder="Demandez une analyse de ce document…" :disabled="sending" aria-label="Message à l’assistant" />
            <button type="submit" class="cx-btn-primary" :disabled="!prompt.trim() || sending">Envoyer</button>
          </form>
          <p class="cx-caption" style="padding-bottom: 12px">{{ provenance === 'frappe-onyx' ? 'Réponse fournie par Onyx via la passerelle Frappe. Les réponses du modèle restent des suggestions; les faits métier doivent être vérifiés par les services ERP.' : 'Les messages sont envoyés à la passerelle Frappe authentifiée. Le modèle et ses outils sont configurés côté serveur.' }}</p>
        </div>

        <div v-else class="cx-section" style="display: grid; gap: 12px">
          <h2 class="m-0 text-base font-semibold">Historique des versions</h2>
          <p class="cx-notice" style="margin: 0">Le contrat d’API actuel ne fournit pas encore de versionnement ni de restauration du brouillon. La version initiale est conservée en mémoire jusqu’à la fermeture de cette page.</p>
          <dl class="cx-dl"><div><dt>Version chargée</dt><dd>{{ item ? formatDate(item.createdAt) : '—' }}</dd></div></dl>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCortexApiClient } from '@/api'
import type { AiDraftItem, ApprovalRequestItem, CopilotMessage, InboundRequestItem } from '@/api/contracts'
import { useSessionStore } from '@/stores/session'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
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
    const api = getCortexApiClient()
    const [kind, sourceId] = id.includes(':') ? id.split(':', 2) : ['', id]
    // Fetch only the requested source: each one has its own permission.
    if (kind === 'inbound') inbound.value = await api.getInboundRequest({ id: sourceId })
    else if (kind === 'draft') draft.value = (await api.listAiDrafts({ page: 1, page_size: 100 })).items.find(row => row.id === sourceId) || null
    else if (kind === 'approval') approval.value = await api.getApprovalRequest({ id: sourceId })
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
function editedField(key: string) { return editedKeys.value.has(key) ? 'cx-field--edited' : '' }
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
