<script setup lang="ts">
import { computed } from 'vue';
import CortexIcon from '../../icons/CortexIcon.vue';
import AiStatusBadge from './AiStatusBadge.vue';
import type { AiStateType } from '../../tokens/colors';

export type ProvenanceSourceType = 'api' | 'realtime' | 'mock' | 'demo' | 'stale';

interface Props {
  sourceType: ProvenanceSourceType;
  endpoint?: string;
  requestId?: string;
  timestamp: string;
  state?: AiStateType;
  sha256Hash?: string;
  documentName?: string;
  locale?: 'fr-CA' | 'en-CA';
  isStale?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  endpoint: undefined,
  requestId: undefined,
  state: 'verified',
  sha256Hash: undefined,
  documentName: undefined,
  locale: 'fr-CA',
  isStale: false,
});

const emit = defineEmits<{
  (e: 'refresh'): void;
  (e: 'view-proof'): void;
}>();

const isFr = computed(() => props.locale === 'fr-CA');

const isSynthetic = computed(() => props.sourceType === 'demo' || props.sourceType === 'mock');

const provenanceLabel = computed(() => {
  switch (props.sourceType) {
    case 'api':
      return isFr.value ? 'Backend Frappe API (En direct)' : 'Frappe Backend API (Live)';
    case 'realtime':
      return isFr.value ? 'Flux temps réel (WebSocket)' : 'Real-time Event (WebSocket)';
    case 'mock':
      return isFr.value ? 'Mock typé (Simulé)' : 'Typed Mock (Simulated)';
    case 'demo':
      return isFr.value ? 'Donnée synthétique (DEMO)' : 'Synthetic Data (DEMO)';
    case 'stale':
      return isFr.value ? 'Donnée potentiellement périmée' : 'Potentially Stale Data';
    default:
      return props.sourceType;
  }
});
</script>

<template>
  <div
    :class="[
      'cx-provenance-card',
      `cx-provenance-card--${sourceType}`,
      { 'cx-provenance-card--stale': isStale || sourceType === 'stale' },
    ]"
    role="region"
    :aria-label="isFr ? 'Provenance des données' : 'Data provenance'"
  >
    <div class="cx-provenance-card__header">
      <div class="cx-provenance-card__source-badge">
        <CortexIcon
          :name="isSynthetic ? 'cpu' : sourceType === 'realtime' ? 'refresh-cw' : 'check-circle'"
          :size="14"
          :color="isSynthetic ? 'var(--cortex-violet-800, #5b21b6)' : 'var(--cortex-green-800, #044727)'"
        />
        <span class="cx-provenance-card__source-title">{{ provenanceLabel }}</span>
        <span v-if="isSynthetic" class="cx-provenance-card__demo-pill">DEMO</span>
      </div>

      <AiStatusBadge
        :state="state"
        :locale="locale"
        :is-demo="isSynthetic"
        size="sm"
      />
    </div>

    <!-- Stale Warning Banner -->
    <div v-if="isStale || sourceType === 'stale'" class="cx-provenance-card__stale-banner">
      <CortexIcon name="alert-triangle" :size="14" color="var(--cortex-warning-800, #92400e)" />
      <span>{{ isFr ? "Donnée locale potentiellement obsolète." : "Local data may be out of date." }}</span>
      <button
        type="button"
        class="cx-provenance-card__refresh-btn"
        @click="emit('refresh')"
      >
        <CortexIcon name="refresh-cw" :size="12" />
        {{ isFr ? "Actualiser" : "Refresh" }}
      </button>
    </div>

    <div class="cx-provenance-card__details">
      <div v-if="endpoint" class="cx-provenance-card__row">
        <span class="cx-provenance-card__key">Endpoint:</span>
        <code class="cx-provenance-card__code">{{ endpoint }}</code>
      </div>

      <div v-if="requestId" class="cx-provenance-card__row">
        <span class="cx-provenance-card__key">Request ID:</span>
        <code class="cx-provenance-card__code">{{ requestId }}</code>
      </div>

      <div class="cx-provenance-card__row">
        <span class="cx-provenance-card__key">{{ isFr ? "Horodatage :" : "Timestamp:" }}</span>
        <span class="cx-provenance-card__val">{{ timestamp }}</span>
      </div>

      <div v-if="documentName" class="cx-provenance-card__row">
        <span class="cx-provenance-card__key">{{ isFr ? "Document source :" : "Source doc:" }}</span>
        <span class="cx-provenance-card__val">{{ documentName }}</span>
        <button
          type="button"
          class="cx-provenance-card__view-proof-btn"
          @click="emit('view-proof')"
        >
          <CortexIcon name="external-link" :size="11" />
          {{ isFr ? "Preuve" : "Proof" }}
        </button>
      </div>

      <div v-if="sha256Hash" class="cx-provenance-card__row">
        <span class="cx-provenance-card__key">SHA-256:</span>
        <code class="cx-provenance-card__code-hash">{{ sha256Hash }}</code>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cx-provenance-card {
  background-color: var(--cortex-surface, #ffffff);
  border: 1px solid var(--cortex-border, #cbdcd2);
  border-radius: var(--radius-md, 8px);
  padding: 12px;
  font-family: var(--font-sans, Inter, sans-serif);
  font-size: 12px;
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(8, 18, 13, 0.04));
  box-sizing: border-box;
}

.cx-provenance-card--demo,
.cx-provenance-card--mock {
  background-color: var(--cortex-surface-subtle, #f2f7f4);
  border-color: var(--cortex-violet-600, #7c3aed);
}

.cx-provenance-card--stale {
  border-color: var(--cortex-warning-600, #d97706);
}

.cx-provenance-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
  flex-wrap: wrap;
}

.cx-provenance-card__source-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--cortex-text, #08120d);
}

.cx-provenance-card__demo-pill {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  background-color: var(--cortex-violet-100, #ede9fe);
  color: var(--cortex-violet-800, #5b21b6);
  border: 1px solid var(--cortex-violet-600, #7c3aed);
  border-radius: 4px;
}

.cx-provenance-card__stale-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 6px 8px;
  background-color: var(--cortex-warning-50, #fffbeb);
  border: 1px solid var(--cortex-warning-500, #f59e0b);
  border-radius: var(--radius-sm, 6px);
  color: var(--cortex-warning-900, #78350f);
  font-size: 11.5px;
  font-weight: 500;
  margin-bottom: 8px;
}

.cx-provenance-card__refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--cortex-warning-900, #78350f);
  background: #ffffff;
  border: 1px solid var(--cortex-warning-600, #d97706);
  border-radius: 4px;
  cursor: pointer;
}

.cx-provenance-card__details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--cortex-text-secondary, #264034);
}

.cx-provenance-card__row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.cx-provenance-card__key {
  color: var(--cortex-text-muted, #436354);
  font-weight: 500;
  min-width: 90px;
}

.cx-provenance-card__code {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 11px;
  background-color: rgba(8, 18, 13, 0.05);
  padding: 1px 4px;
  border-radius: 3px;
  color: var(--cortex-text, #08120d);
}

.cx-provenance-card__code-hash {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 10px;
  color: var(--cortex-text-muted, #436354);
  word-break: break-all;
}

.cx-provenance-card__view-proof-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--cortex-violet-800, #5b21b6);
  background: #ffffff;
  border: 1px solid var(--cortex-violet-600, #7c3aed);
  border-radius: 4px;
  cursor: pointer;
}
</style>
