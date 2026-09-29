<template>
  <div class="cx-chat-blocks">
    <template v-for="(block, index) in blocks" :key="index">
      <p v-if="block.type === 'assistant_text'" class="cx-chat-text" data-block="assistant_text">{{ str(block.text) }}</p>

      <section v-else-if="block.type === 'verified_fact'" class="cx-chat-card cx-chat-card--verified" data-block="verified_fact">
        <h4><ShieldCheck :size="14" aria-hidden="true" /> {{ str(block.title) }} <span class="cx-tag cx-tag--ok">Vérifié dans Cortex</span></h4>
        <ul><li v-for="item in list(block.items)" :key="item">{{ item }}</li></ul>
      </section>

      <section v-else-if="block.type === 'extracted_data'" class="cx-chat-card" data-block="extracted_data">
        <h4><FileText :size="14" aria-hidden="true" /> {{ str(block.title) }} <span class="cx-tag">Extrait de la source</span></h4>
        <dl class="cx-dl"><div v-for="field in fields(block.fields)" :key="field.label"><dt>{{ field.label }}</dt><dd>{{ field.value }} <span class="cx-tag" :class="field.confidence === 'high' ? 'cx-tag--ok' : field.confidence === 'low' ? 'cx-tag--warn' : ''">{{ confidenceLabel(field.confidence) }}</span></dd></div></dl>
      </section>

      <section v-else-if="block.type === 'proposal'" class="cx-chat-card" data-block="proposal">
        <h4><Sparkles :size="14" aria-hidden="true" /> {{ str(block.title) }} <span class="cx-tag cx-tag--warn">Proposé — non exécuté</span></h4>
        <p>{{ str(block.summary) }}</p>
        <ul v-if="list(block.impact).length"><li v-for="item in list(block.impact)" :key="item">{{ item }}</li></ul>
        <p v-if="block.requires_approval" class="cx-caption">Une approbation humaine est requise avant toute exécution.</p>
        <RouterLink v-if="block.action === 'open_quote_composer'" class="cx-btn-soft" to="/app/cortex-rental/new">Ouvrir le compositeur</RouterLink>
      </section>

      <section v-else-if="block.type === 'approval_required'" class="cx-chat-card cx-chat-card--warn" data-block="approval_required">
        <h4><Lock :size="14" aria-hidden="true" /> {{ str(block.action_label) }} <span class="cx-tag cx-tag--warn">Approbation requise</span></h4>
        <ul><li v-for="req in requirements(block.requirements)" :key="req.label">{{ req.passed ? '✓' : '✗' }} {{ req.label }}</li></ul>
        <RouterLink class="cx-btn-soft" to="/app/cortex-ai-inbox?type=approval">Ouvrir la file d'approbation</RouterLink>
      </section>

      <section v-else-if="block.type === 'risk'" class="cx-chat-card" :class="block.severity === 'danger' ? 'cx-chat-card--bad' : 'cx-chat-card--warn'" data-block="risk">
        <h4><TriangleAlert :size="14" aria-hidden="true" /> {{ str(block.title) }}</h4>
        <p>{{ str(block.explanation) }}</p>
      </section>

      <section v-else-if="block.type === 'missing_information'" class="cx-chat-card cx-chat-card--warn" data-block="missing_information">
        <h4><CircleHelp :size="14" aria-hidden="true" /> Il manque des informations <span class="cx-tag cx-tag--warn">À confirmer</span></h4>
        <ul><li v-for="item in list(block.fields)" :key="item">{{ item }}</li></ul>
        <p v-if="block.suggested_next_action" class="cx-caption">{{ str(block.suggested_next_action) }}</p>
      </section>

      <p v-else-if="block.type === 'tool_progress'" class="cx-chat-progress" data-block="tool_progress" role="status">
        <LoaderCircle v-if="block.state === 'running'" :size="14" class="animate-spin" aria-hidden="true" />
        {{ str(block.message) || str(block.tool_name) }}
      </p>

      <section v-else class="cx-chat-card cx-chat-card--bad" data-block="error" role="alert">
        <h4><ShieldAlert :size="14" aria-hidden="true" /> {{ block.type === 'error' ? str(block.title) || 'Une erreur est survenue' : 'Contenu non reconnu' }}</h4>
        <p>{{ block.type === 'error' ? str(block.safe_message) : `Type de bloc : ${block.type}` }}</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { CircleHelp, FileText, LoaderCircle, Lock, ShieldAlert, ShieldCheck, Sparkles, TriangleAlert } from 'lucide-vue-next'
import type { ChatBlockData } from '@/features/intelligence/aiChatGateway'

defineProps<{ blocks: ChatBlockData[] }>()

// Blocks come from the server, but rendering never trusts their shape: every read is coerced and text stays text (no v-html).
const str = (value: unknown): string => (typeof value === 'string' ? value : '')
const list = (value: unknown): string[] => (Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [])
const fields = (value: unknown): Array<{ label: string; value: string; confidence: string }> =>
  Array.isArray(value) ? value.map((v) => ({ label: str(v?.label), value: str(v?.value), confidence: str(v?.confidence) })) : []
const requirements = (value: unknown): Array<{ label: string; passed: boolean }> => (Array.isArray(value) ? value.map((v) => ({ label: str(v?.label), passed: v?.passed === true })) : [])
const confidenceLabel = (level: string) => ({ high: 'Confiance élevée', medium: 'Confiance moyenne', low: 'Confiance faible' })[level] ?? level
</script>

<style scoped>
.cx-chat-blocks { display: grid; gap: 10px; }
.cx-chat-text { margin: 0; white-space: pre-wrap; line-height: 1.55; }
.cx-chat-card { padding: 12px 14px; border: 1px solid var(--erp-border, #e5e7eb); border-radius: 8px; background: #fff; font-size: 13px; }
.cx-chat-card h4 { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 0 0 6px; font-size: 13px; font-weight: 600; }
.cx-chat-card p { margin: 0 0 6px; }
.cx-chat-card ul { margin: 0 0 6px; padding-left: 18px; }
.cx-chat-card--verified { border-color: #087a43; }
.cx-chat-card--warn { border-color: #b45309; }
.cx-chat-card--bad { border-color: #b3191f; }
.cx-chat-progress { display: flex; align-items: center; gap: 6px; margin: 0; color: var(--erp-muted, #525252); font-size: 12px; }
</style>
