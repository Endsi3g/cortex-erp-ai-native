<template>
  <div class="cx-page" data-test="screen-ai-audit">
    <CortexPageHeader title="AI Audit" subtitle="Décisions, preuves et exécutions disponibles dans les journaux Cortex.">
      <template #actions>
        <RefreshButton :loading="loading" @refresh="load" />
        <button type="button" class="cx-btn-soft" @click="exportCsv">Exporter CSV</button>
        <button type="button" class="cx-btn-soft" @click="printReport">Imprimer / PDF</button>
      </template>
    </CortexPageHeader>

    <div class="cx-filters print:hidden">
      <FilterField label="Type de détails"><select v-model="viewMode" class="cx-field"><option v-for="mode in modes" :key="mode.value" :value="mode.value">{{ mode.label }}</option></select></FilterField>
      <FilterField label="Agent ou acteur"><select v-model="agentFilter" class="cx-field"><option v-for="o in agentOptions" :key="o.value" :value="o.value">{{ o.label }}</option></select></FilterField>
      <FilterField label="Action"><select v-model="actionFilter" class="cx-field"><option v-for="o in actionOptions" :key="o.value" :value="o.value">{{ o.label }}</option></select></FilterField>
      <FilterField label="Date"><input v-model="dateFilter" type="date" class="cx-field" /></FilterField>
    </div>

    <div v-if="error" class="cx-notice" role="alert">{{ error }}</div>

    <div class="cx-tablewrap">
      <table class="cx-table">
        <thead>
          <tr><th scope="col" class="cx-rownum">#</th><th scope="col">Date</th><th scope="col">Agent / acteur</th><th scope="col">Action</th><th scope="col">Entité</th><th scope="col">Résultat</th><th scope="col" class="num">Latence</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, index) in filtered"
            :key="row.id"
            tabindex="0"
            class="cx-clickable"
            :aria-selected="selected?.id === row.id"
            @click="selected = selected?.id === row.id ? null : row"
            @keydown.enter="selected = selected?.id === row.id ? null : row"
            @keydown.space.prevent="selected = selected?.id === row.id ? null : row"
          >
            <td class="cx-rownum">{{ index + 1 }}</td>
            <td class="whitespace-nowrap">{{ formatDate(row.timestamp) }}</td>
            <td><div class="font-medium">{{ row.actor }}</div><div class="text-xs" style="color: var(--erp-muted)">{{ row.actorId }}</div></td>
            <td class="font-mono text-xs">{{ row.action }}</td>
            <td>{{ row.entity }}</td>
            <td><span class="cx-tag" :class="row.success ? 'cx-tag--ok' : 'cx-tag--bad'">{{ row.success ? 'Réussi' : 'Échec / refus' }}</span></td>
            <td class="num">{{ row.latency ? `${row.latency} ms` : '—' }}</td>
          </tr>
          <tr v-if="loading"><td colspan="7" class="cx-empty">Chargement du journal…</td></tr>
          <tr v-else-if="filtered.length === 0"><td colspan="7" class="cx-empty"><strong>Aucun événement d’audit</strong>Aucun événement ne correspond à ces filtres.</td></tr>
        </tbody>
      </table>
      <p class="cx-caption">{{ filtered.length }} événement(s). Les données sensibles sont masquées dans les détails.</p>
    </div>

    <section v-if="selected" class="cx-section" aria-label="Détail de l’événement d’audit">
      <div class="flex items-start justify-between gap-3">
        <div><h2 style="margin: 0">{{ selected.action }}</h2><p class="m-0 mt-1 text-xs" style="color: var(--erp-muted)">Request ID: <span class="font-mono">{{ selected.requestId }}</span></p></div>
        <button type="button" class="cx-btn-soft cx-btn-icon print:hidden" aria-label="Fermer le détail" @click="selected = null">✕</button>
      </div>
      <p v-if="selected.summary" class="mt-3 text-sm">{{ maskSensitive(selected.summary) }}</p>
      <p v-if="selected.hash" class="mt-3 text-sm">Hash SHA-256: <code class="break-all font-mono">{{ selected.hash }}</code></p>
      <div v-if="selected.tools?.length" class="mt-4 cx-tablewrap">
        <table class="cx-table" aria-label="Outils appelés">
          <thead><tr><th scope="col">Outil</th><th scope="col" class="num">Latence</th><th scope="col">Résultat</th></tr></thead>
          <tbody><tr v-for="tool in selected.tools" :key="tool.tool_name"><td>{{ tool.tool_name }}</td><td class="num">{{ tool.latency_ms != null ? `${tool.latency_ms} ms` : '—' }}</td><td>{{ tool.status }}</td></tr></tbody>
        </table>
      </div>
      <dl v-if="viewMode === 'technical'" class="cx-dl mt-4">
        <div><dt>Modèle</dt><dd>{{ selected.model || 'Non fourni' }}</dd></div>
        <div><dt>Tokens</dt><dd>{{ selected.tokens ?? 'Non fourni' }}</dd></div>
        <div><dt>Coût</dt><dd>{{ selected.cost ?? 'Non fourni' }}</dd></div>
        <div><dt>Politique</dt><dd>{{ selected.policy || 'Non fournie' }}</dd></div>
      </dl>
    </section>

    <p class="cx-caption" style="padding-bottom: 24px">Les événements proviennent du journal métier et de la télémétrie disponibles via l’API Cortex. Onyx doit transmettre son identifiant d’exécution et sa latence dans le même flux d’audit.</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCortexApiClient } from '@/api'
import type { AgentRunTelemetry, AuditEvent } from '@/api/contracts'
import { useSessionStore } from '@/stores/session'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import FilterField from '@/features/common/components/FilterField.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'

interface AuditRow { id: string; timestamp: string; actor: string; actorId: string; action: string; entity: string; success: boolean; latency?: number; requestId: string; summary?: string; hash?: string; model?: string; tokens?: number; cost?: string; policy?: string; tools?: AgentRunTelemetry['tools_invoked'] }
const session = useSessionStore()
const loading = ref(false)
const error = ref('')
const rows = ref<AuditRow[]>([])
const selected = ref<AuditRow | null>(null)
const viewMode = ref<'operational' | 'technical'>('operational')
const agentFilter = ref('all')
const actionFilter = ref('all')
const dateFilter = ref('')
const modes = [{ value: 'operational', label: 'Vue opérationnelle' }, { value: 'technical', label: 'Vue technique' }] as const
const agents = computed(() => [...new Set(rows.value.map(row => row.actor))].sort())
const actions = computed(() => [...new Set(rows.value.map(row => row.action))].sort())
const agentOptions = computed(() => [{ label: 'Tous les agents', value: 'all' }, ...agents.value.map(agent => ({ label: agent, value: agent }))])
const actionOptions = computed(() => [{ label: 'Toutes les actions', value: 'all' }, ...actions.value.map(action => ({ label: action, value: action }))])
const filtered = computed(() => rows.value.filter(row => (agentFilter.value === 'all' || row.actor === agentFilter.value) && (actionFilter.value === 'all' || row.action === actionFilter.value) && (!dateFilter.value || row.timestamp.startsWith(dateFilter.value))))
async function load() {
  loading.value = true; error.value = ''
  try {
    const api = getCortexApiClient()
    const [audit, activity] = await Promise.all([api.listAuditEvents({ page: 1, page_size: 100 }), api.getAgentActivity({ limit: 100 }).catch(() => null)])
    const auditRows = audit.events.map((event: AuditEvent): AuditRow => ({ id: `audit:${event.id}`, timestamp: event.timestamp, actor: event.actor.actor_name || (event.actor.actor_type === 'Agent' ? 'Agent métier' : event.actor.actor_type), actorId: event.actor.actor_id, action: event.action, entity: `${event.entity_type} · ${event.entity_id}`, success: event.policy_execution?.passed !== false, requestId: event.request_id, summary: event.diff_summary, hash: event.evidence_hash_sha256, policy: event.policy_execution?.policy_name }))
    const runRows = (activity?.runs ?? []).map((run: AgentRunTelemetry): AuditRow => ({ id: `run:${run.run_id}`, timestamp: run.started_at, actor: run.agent_name.replace(/^Cortex\s+/, ''), actorId: run.run_id, action: 'agent.run', entity: 'Exécution agent', success: run.status === 'completed', latency: run.duration_ms, requestId: run.run_id, model: run.model_used, tokens: run.prompt_tokens != null && run.completion_tokens != null ? run.prompt_tokens + run.completion_tokens : undefined, cost: run.total_cost_cad != null ? `${run.total_cost_cad.toFixed(4)} CAD` : undefined, tools: run.tools_invoked }))
    rows.value = [...auditRows, ...runRows].sort((a, b) => b.timestamp.localeCompare(a.timestamp))
  } catch (cause) { error.value = cause instanceof Error ? cause.message : 'Impossible de charger AI Audit.' }
  finally { loading.value = false }
}
function formatDate(value: string) { return new Intl.DateTimeFormat(session.locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
function maskSensitive(value: string) { return value.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[courriel masqué]').replace(/\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b/g, '[téléphone masqué]') }
function csvCell(value: unknown) {
  const raw = String(value ?? '')
  const safe = /^[\t\r ]*[=+\-@]/.test(raw) ? `'${raw}` : raw
  return `"${safe.replaceAll('"', '""')}"`
}
function exportCsv() {
  const header = ['timestamp', 'actor', 'actor_id', 'action', 'entity', 'success', 'latency_ms', 'request_id', 'summary', 'evidence_sha256']
  const content = [header, ...filtered.value.map(row => [row.timestamp, row.actor, row.actorId, row.action, row.entity, row.success, row.latency, row.requestId, maskSensitive(row.summary || ''), row.hash])].map(line => line.map(csvCell).join(',')).join('\r\n')
  const blob = new Blob([`\uFEFF${content}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `cortex-ai-audit-${new Date().toISOString().slice(0, 10)}.csv`; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
function printReport() { window.print() }
onMounted(load)
</script>

<style>
@media print {
  .cx-page .print\:hidden, .cx-page .cx-titlebar .cx-actions { display: none !important; }
  .cx-table { font-size: 9pt !important; }
  .cx-table tr { break-inside: avoid; }
}
</style>
