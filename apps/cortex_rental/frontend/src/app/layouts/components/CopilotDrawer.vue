<template>
  <!-- Non-modal Contextual Copilot Drawer (416px) -->
  <aside
    v-if="copilotStore.isOpen"
    class="fixed inset-y-0 right-0 z-40 w-full max-w-[416px] bg-cortex-surface border-l border-cortex-border shadow-2xl flex flex-col transition-transform duration-200 ease-in-out font-sans"
    aria-label="Cortex Copilot Drawer"
    role="complementary"
  >
    <!-- Drawer Header -->
    <div class="flex items-center justify-between px-4 py-3.5 border-b border-cortex-border bg-cortex-surface-subtle">
      <div class="flex items-center gap-2">
        <div class="p-1.5 rounded-lg bg-cortex-primary-100 text-cortex-primary-700">
          <Sparkles class="w-4 h-4" />
        </div>
        <div class="flex flex-col">
          <div class="flex items-center gap-1.5">
            <h2 class="text-xs font-bold text-cortex-text-primary tracking-tight">
              {{ t('copilot.title') }}
            </h2>
            <span class="text-[9px] font-mono px-1 py-0.2 rounded bg-cortex-primary-50 text-cortex-primary-700 border border-cortex-primary-200">
              v1.0
            </span>
          </div>
          <span class="text-[10px] text-cortex-text-muted">
            {{ t('copilot.subtitle') }}
          </span>
        </div>
      </div>

      <div class="flex items-center gap-1">
        <button
          type="button"
          @click="copilotStore.close"
          class="p-1.5 rounded-lg text-cortex-text-muted hover:text-cortex-text-primary hover:bg-cortex-surface transition-colors focus:outline-none focus:ring-2 focus:ring-cortex-primary-500"
          :title="t('copilot.close_drawer')"
          aria-label="Fermer le tiroir copilote"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Active Entity Context Bar -->
    <div class="px-4 py-2 bg-cortex-primary-50/50 border-b border-cortex-border flex items-center justify-between text-xs">
      <div class="flex items-center gap-1.5 truncate">
        <span class="text-[10px] text-cortex-text-muted uppercase font-semibold">
          {{ t('copilot.active_context') }}:
        </span>
        <span class="font-mono font-medium text-cortex-primary-900 bg-cortex-surface px-1.5 py-0.5 rounded border border-cortex-border truncate max-w-[200px]">
          {{ copilotStore.formattedContextLabel }}
        </span>
      </div>

      <!-- State Indicator Pill -->
      <span class="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-cortex-primary-100 text-cortex-primary-800">
        <span class="w-1.5 h-1.5 rounded-full bg-cortex-primary-500 animate-pulse"></span>
        {{ copilotStore.canonicalState }}
      </span>
    </div>

    <!-- Message Conversation List -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3.5 bg-cortex-bg">
      <div
        v-for="msg in copilotStore.messages"
        :key="msg.id"
        class="flex flex-col space-y-1"
        :class="msg.sender === 'user' ? 'items-end' : 'items-start'"
      >
        <!-- User Bubble -->
        <div
          v-if="msg.sender === 'user'"
          class="max-w-[85%] rounded-2xl rounded-tr-xs bg-cortex-ink-900 text-white px-3.5 py-2.5 text-xs shadow-xs"
        >
          {{ msg.content }}
        </div>

        <!-- Assistant Bubble with Canonical State Card -->
        <div
          v-else
          class="max-w-[95%] rounded-2xl rounded-tl-xs bg-cortex-surface border border-cortex-border p-3.5 text-xs shadow-xs space-y-2.5 text-cortex-text-primary"
        >
          <div class="flex items-center justify-between border-b border-cortex-border pb-1.5 text-[10px]">
            <span class="font-semibold text-cortex-primary-700 flex items-center gap-1">
              <Sparkles class="w-3 h-3" /> Onyx AI Assistant
            </span>
            <span v-if="msg.confidenceScore" class="font-mono text-cortex-text-muted">
              Confiance: {{ (msg.confidenceScore * 100).toFixed(0) }}%
            </span>
          </div>

          <p class="leading-relaxed whitespace-pre-wrap">
            {{ msg.content }}
          </p>

          <!-- Canonical AI State Card Preview -->
          <div
            v-if="msg.state"
            class="p-2.5 rounded-lg border text-[11px] flex items-start gap-2"
            :class="getStateStyle(msg.state)"
          >
            <component :is="getStateIcon(msg.state)" class="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div class="flex flex-col">
              <span class="font-semibold">{{ getStateLabel(msg.state) }}</span>
              <span v-if="msg.evidenceId" class="text-[10px] font-mono opacity-80">
                Preuve d'audit: {{ msg.evidenceId }}
              </span>
            </div>
          </div>
        </div>

        <span class="text-[9px] text-cortex-text-muted px-1 font-mono">
          {{ new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
        </span>
      </div>

      <!-- Streaming Indicator -->
      <div v-if="copilotStore.isStreaming" class="flex items-center gap-2 text-xs text-cortex-text-muted p-2">
        <Loader2 class="w-4 h-4 animate-spin text-cortex-primary-600" />
        <span>Onyx analyse les politiques et l'inventaire...</span>
      </div>
    </div>

    <!-- Quick Action Pills -->
    <div class="px-4 py-2 border-t border-cortex-border bg-cortex-surface space-y-1.5">
      <div class="text-[10px] uppercase font-semibold text-cortex-text-muted">
        Actions suggérées
      </div>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="pill in quickActions"
          :key="pill.text"
          type="button"
          @click="copilotStore.sendMessage(pill.text)"
          class="px-2 py-1 text-[11px] rounded-lg border border-cortex-border bg-cortex-surface-subtle hover:bg-cortex-primary-50 hover:border-cortex-primary-300 hover:text-cortex-primary-900 transition-colors text-left"
        >
          {{ pill.label }}
        </button>
      </div>
    </div>

    <!-- Input Composer -->
    <div class="p-3 border-t border-cortex-border bg-cortex-surface">
      <form @submit.prevent="handleSend" class="flex items-center gap-2">
        <input
          v-model="inputQuery"
          type="text"
          placeholder="Poser une question ou demander une action..."
          class="flex-1 px-3 py-2 text-xs rounded-xl border border-cortex-border bg-cortex-surface-subtle text-cortex-text-primary placeholder:text-cortex-text-muted focus:outline-none focus:ring-2 focus:ring-cortex-primary-500 focus:bg-cortex-surface transition-colors font-sans"
        />
        <button
          type="submit"
          :disabled="!inputQuery.trim() || copilotStore.isStreaming"
          class="p-2 rounded-xl bg-cortex-primary-600 text-white hover:bg-cortex-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none shadow-xs"
          aria-label="Envoyer le message"
        >
          <Send class="w-4 h-4" />
        </button>
      </form>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Sparkles,
  X,
  Send,
  Loader2,
  CheckCircle,
  FileText,
  AlertTriangle,
  Lock,
  ShieldCheck,
  ShieldAlert
} from 'lucide-vue-next'
import { useCopilotStore, type CopilotCanonicalState } from '@/stores/copilot'

const { t } = useI18n()
const copilotStore = useCopilotStore()

const inputQuery = ref('')

const quickActions = [
  { label: '🔍 Vérifier disponibilité', text: 'Vérifier la disponibilité pour les dates sélectionnées' },
  { label: '⚡ Optimiser tarif 7j=3j', text: 'Appliquer la courbe tarifaire hebdomadaire 7 jours pour 3 facturés' },
  { label: '🛡️ Contrôler assurance', text: 'Vérifier la validité de l\'attestation d\'assurance du client' }
]

const handleSend = () => {
  if (inputQuery.value.trim() && !copilotStore.isStreaming) {
    const text = inputQuery.value
    inputQuery.value = ''
    copilotStore.sendMessage(text)
  }
}

const getStateStyle = (state: CopilotCanonicalState) => {
  switch (state) {
    case 'verified':
    case 'approved_executed':
      return 'bg-cortex-primary-50 border-cortex-primary-300 text-cortex-primary-900'
    case 'extracted':
      return 'bg-purple-50 border-purple-300 text-purple-900'
    case 'proposed':
      return 'bg-emerald-50 border-emerald-300 text-emerald-900'
    case 'needs_confirmation':
    case 'approval_required':
      return 'bg-amber-50 border-amber-300 text-amber-900'
    case 'blocked_by_policy':
    case 'failed':
      return 'bg-red-50 border-red-300 text-red-900'
    default:
      return 'bg-cortex-surface-subtle border-cortex-border text-cortex-text-primary'
  }
}

const getStateIcon = (state: CopilotCanonicalState) => {
  switch (state) {
    case 'verified':
      return CheckCircle
    case 'extracted':
      return FileText
    case 'proposed':
      return Sparkles
    case 'needs_confirmation':
      return AlertTriangle
    case 'approval_required':
      return Lock
    case 'approved_executed':
      return ShieldCheck
    case 'blocked_by_policy':
    case 'failed':
      return ShieldAlert
    default:
      return Sparkles
  }
}

const getStateLabel = (state: CopilotCanonicalState) => {
  switch (state) {
    case 'verified':
      return 'Vérifié dans Cortex'
    case 'extracted':
      return 'Extrait de la source'
    case 'proposed':
      return 'Proposé — non exécuté'
    case 'needs_confirmation':
      return 'À confirmer'
    case 'approval_required':
      return 'Approbation requise'
    case 'approved_executed':
      return 'Approuvé et exécuté'
    case 'blocked_by_policy':
      return 'Bloqué par policy'
    default:
      return state
  }
}
</script>
