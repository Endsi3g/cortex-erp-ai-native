<template>
  <section class="mx-auto max-w-[1600px] space-y-4" data-test="screen-ai-audit">
    <header class="flex flex-wrap items-end justify-between gap-3 border-b border-cortex-border pb-3">
      <div><h1 class="text-xl font-semibold">AI Audit</h1><p class="mt-1 text-xs text-cortex-text-secondary">Historique des décisions, preuves et exécutions disponibles dans les journaux Cortex.</p></div>
      <div class="flex items-center gap-2"><Button size="sm" variant="subtle" :loading="loading" @click="load">Actualiser</Button><Button size="sm" variant="subtle" @click="exportCsv">Exporter CSV</Button><Button size="sm" variant="solid" theme="green" @click="printReport">Exporter PDF</Button></div>
    </header>
    <div class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-cortex-border bg-white p-2.5 print:hidden">
      <TabButtons v-model="viewMode" :buttons="modeButtons" aria-label="Type de détails d’audit" />
      <div class="flex flex-wrap gap-2"><Select v-model="agentFilter" class="min-w-40" size="sm" variant="outline" aria-label="Filtrer par agent" :options="agentOptions" /><Select v-model="actionFilter" class="min-w-40" size="sm" variant="outline" aria-label="Filtrer par action" :options="actionOptions" /><TextInput v-model="dateFilter" type="date" size="sm" variant="outline" aria-label="Filtrer par date" /></div>
    </div>
    <div v-if="error" class="rounded border border-red-200 bg-red-50 p-3 text-xs text-red-900" role="alert">{{ error }}</div>
    <div class="overflow-hidden rounded-md border border-cortex-border bg-white">
      <div class="flex items-center justify-between border-b border-cortex-border bg-cortex-surface-subtle/60 px-3 py-2 text-xs"><span>{{ filtered.length }} événement(s)</span><span class="text-[10px] text-cortex-text-muted">Les données sensibles sont masquées dans les détails.</span></div>
      <div class="overflow-x-auto">
        <table class="w-full border-collapse text-left text-xs"><thead class="bg-white text-[10px] uppercase tracking-wide text-cortex-text-muted"><tr><th class="px-3 py-2">Date</th><th class="px-3 py-2">Agent / Acteur</th><th class="px-3 py-2">Action</th><th class="px-3 py-2">Entité</th><th class="px-3 py-2">Résultat</th><th class="px-3 py-2">Latence</th></tr></thead><tbody>
          <tr v-for="row in filtered" :key="row.id" tabindex="0" class="cursor-pointer border-t border-cortex-border/70 hover:bg-cortex-surface-subtle/60 focus:bg-cortex-primary-50" @click="selected = selected?.id === row.id ? null : row" @keydown.enter="selected = selected?.id === row.id ? null : row" @keydown.space.prevent="selected = selected?.id === row.id ? null : row"><td class="whitespace-nowrap px-3 py-2.5">{{ formatDate(row.timestamp) }}</td><td class="px-3 py-2.5"><div class="font-medium">{{ row.actor }}</div><div class="text-[10px] text-cortex-text-muted">{{ row.actorId }}</div></td><td class="px-3 py-2.5 font-mono text-[11px]">{{ row.action }}</td><td class="px-3 py-2.5">{{ row.entity }}</td><td class="px-3 py-2.5"><Badge :theme="row.success ? 'green' : 'red'" variant="subtle">{{ row.success ? 'Réussi' : 'Échec / refus' }}</Badge></td><td class="px-3 py-2.5 font-mono">{{ row.latency ? `${row.latency} ms` : '—' }}</td></tr>
          <tr v-if="!loading && filtered.length === 0"><td colspan="6" class="p-12 text-center text-xs text-cortex-text-muted">Aucun événement d’audit.</td></tr>
        </tbody></table>
      </div>
        <section v-if="selected" class="border-t border-cortex-border bg-[#fbfdfb] p-4" aria-label="Détail de l’événement d’audit"><div class="flex items-start justify-between"><div><h2 class="text-sm font-semibold">{{ selected.action }}</h2><p class="mt-1 text-[10px] text-cortex-text-muted">Request ID : <span class="font-mono">{{ selected.requestId }}</span></p></div><Button class="print:hidden" size="sm" variant="ghost" icon="x" aria-label="Fermer le détail" @click="selected = null" /></div><p v-if="selected.summary" class="mt-3 text-xs">{{ maskSensitive(selected.summary) }}</p><div v-if="selected.hash" class="mt-3 text-xs">Hash SHA-256 : <code class="break-all font-mono">{{ selected.hash }}</code></div><div v-if="selected.tools?.length" class="mt-4"><h3 class="mb-2 text-xs font-semibold">Outils appelés</h3><div v-for="tool in selected.tools" :key="tool.tool_name" class="grid grid-cols-[1fr_auto_auto] gap-4 border-t border-cortex-border py-2 text-xs"><span>{{ tool.tool_name }}</span><span>{{ tool.latency_ms }} ms</span><span>{{ tool.status }}</span></div></div><div v-if="viewMode === 'technical'" class="mt-4 grid grid-cols-2 gap-3 text-xs"><div><span class="text-cortex-text-muted">Modèle</span><p>{{ selected.model || 'Non fourni' }}</p></div><div><span class="text-cortex-text-muted">Tokens</span><p>{{ selected.tokens ?? 'Non fourni' }}</p></div><div><span class="text-cortex-text-muted">Coût</span><p>{{ selected.cost ?? 'Non fourni' }}</p></div><div><span class="text-cortex-text-muted">Policy</span><p>{{ selected.policy || 'Non fournie' }}</p></div></div></section>
    </div>
    <p class="text-[10px] text-cortex-text-muted">Les événements affichés proviennent du journal métier et de la télémétrie disponibles via Cortex API. Onyx doit transmettre son identifiant d’exécution et sa latence dans le même flux d’audit.</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Badge, Button, Select, TabButtons, TextInput } from 'frappe-ui'
import { getCortexApiClient } from '@/api'
import type { AgentRunTelemetry, AuditEvent } from '@/api/contracts'
import { useSessionStore } from '@/stores/session'

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
const modeButtons = modes.map(mode => ({ label: mode.label, value: mode.value, theme: 'gray' as const, variant: 'subtle' as const }))
const agentOptions = computed(() => [{ label: 'Tous les agents', value: 'all' }, ...agents.value.map(agent => ({ label: agent, value: agent }))])
const actionOptions = computed(() => [{ label: 'Toutes les actions', value: 'all' }, ...actions.value.map(action => ({ label: action, value: action }))])
const filtered = computed(() => rows.value.filter(row => (agentFilter.value === 'all' || row.actor === agentFilter.value) && (actionFilter.value === 'all' || row.action === actionFilter.value) && (!dateFilter.value || row.timestamp.startsWith(dateFilter.value))))
async function load() {
  loading.value = true; error.value = ''
  try {
    const api = getCortexApiClient()
    const [audit, activity] = await Promise.all([api.listAuditEvents({ page: 1, page_size: 100 }), api.getAgentActivity({ limit: 100 })])
    const auditRows = audit.events.map((event: AuditEvent): AuditRow => ({ id: `audit:${event.id}`, timestamp: event.timestamp, actor: event.actor.actor_name || (event.actor.actor_type === 'Agent' ? 'Agent métier' : event.actor.actor_type), actorId: event.actor.actor_id, action: event.action, entity: `${event.entity_type} · ${event.entity_id}`, success: event.policy_execution?.passed !== false, requestId: event.request_id, summary: event.diff_summary, hash: event.evidence_hash_sha256, policy: event.policy_execution?.policy_name }))
    const runRows = activity.runs.map((run: AgentRunTelemetry): AuditRow => ({ id: `run:${run.run_id}`, timestamp: run.started_at, actor: run.agent_name.replace(/^Cortex\s+/, ''), actorId: run.run_id, action: 'agent.run', entity: 'Exécution agent', success: run.status === 'completed', latency: run.duration_ms, requestId: run.run_id, model: run.model_used, tokens: run.prompt_tokens + run.completion_tokens, cost: `${run.total_cost_cad.toFixed(4)} CAD`, tools: run.tools_invoked }))
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
  body { background: #fff !important; }
  aside, nav, header button, .print\:hidden { display: none !important; }
  main { overflow: visible !important; padding: 0 !important; }
  section { max-width: none !important; }
  table { font-size: 9pt !important; }
  tr { break-inside: avoid; }
}
</style>
