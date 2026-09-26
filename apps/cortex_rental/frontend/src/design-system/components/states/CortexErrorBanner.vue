<script setup lang="ts">
import { computed } from 'vue';
import CortexIcon from '../../icons/CortexIcon.vue';
import CortexButton from '../base/CortexButton.vue';

interface Props {
  title?: string;
  errorMessage: string;
  nonMutationMessage?: string;
  errorCode?: string;
  requestId?: string;
  retryable?: boolean;
  dismissible?: boolean;
  locale?: 'fr-CA' | 'en-CA';
}

const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  nonMutationMessage: undefined,
  errorCode: undefined,
  requestId: undefined,
  retryable: false,
  dismissible: false,
  locale: 'fr-CA',
});

const emit = defineEmits<{
  (e: 'retry'): void;
  (e: 'dismiss'): void;
}>();

const isFr = computed(() => props.locale === 'fr-CA');

const defaultTitle = computed(() => {
  return isFr.value ? "L'opération n'a pas pu être effectuée" : "Operation could not be completed";
});

const defaultNonMutation = computed(() => {
  return isFr.value
    ? "Aucune modification n'a été enregistrée dans la base de données Cortex."
    : "No changes have been committed to the Cortex database.";
});
</script>

<template>
  <div class="cx-error-banner" role="alert" aria-live="assertive">
    <div class="cx-error-banner__icon" aria-hidden="true">
      <CortexIcon name="alert-circle" :size="20" color="var(--cortex-danger-700, #b91c1c)" />
    </div>

    <div class="cx-error-banner__content">
      <h4 class="cx-error-banner__title">{{ title || defaultTitle }}</h4>
      
      <!-- 2-Part Rule: Part 1 - What failed -->
      <p class="cx-error-banner__message">{{ errorMessage }}</p>

      <!-- 2-Part Rule: Part 2 - What was NOT modified -->
      <p class="cx-error-banner__non-mutation">
        <CortexIcon name="shield" :size="13" color="var(--cortex-danger-900, #7f1d1d)" />
        <span>{{ nonMutationMessage || defaultNonMutation }}</span>
      </p>

      <!-- Technical Metadata: Code & Request ID -->
      <div v-if="errorCode || requestId" class="cx-error-banner__meta">
        <span v-if="errorCode" class="cx-error-banner__code">
          Code: <code>{{ errorCode }}</code>
        </span>
        <span v-if="requestId" class="cx-error-banner__request-id">
          Request ID: <code>{{ requestId }}</code>
        </span>
      </div>

      <!-- Actions -->
      <div v-if="retryable || $slots.actions" class="cx-error-banner__actions">
        <slot name="actions">
          <CortexButton
            v-if="retryable"
            variant="destructive"
            size="sm"
            icon="refresh-cw"
            @click="emit('retry')"
          >
            {{ isFr ? 'Réessayer l’opération' : 'Retry operation' }}
          </CortexButton>
        </slot>
      </div>
    </div>

    <!-- Dismiss button -->
    <button
      v-if="dismissible"
      type="button"
      class="cx-error-banner__dismiss"
      aria-label="Fermer l'alerte d'erreur"
      @click="emit('dismiss')"
    >
      <CortexIcon name="x" :size="16" />
    </button>
  </div>
</template>

<style scoped>
.cx-error-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3, 12px);
  padding: var(--space-4, 16px);
  background-color: var(--cortex-danger-50, #fef2f2);
  border: 1.5px solid var(--cortex-danger-600, #dc2626);
  border-radius: var(--radius-md, 8px);
  font-family: var(--font-sans, Inter, sans-serif);
  color: var(--cortex-text, #08120d);
  box-sizing: border-box;
  margin-bottom: var(--space-4, 16px);
}

.cx-error-banner__icon {
  flex-shrink: 0;
  margin-top: 1px;
}

.cx-error-banner__content {
  flex-grow: 1;
}

.cx-error-banner__title {
  margin: 0 0 4px 0;
  font-size: 14.5px;
  font-weight: 700;
  color: var(--cortex-danger-900, #7f1d1d);
}

.cx-error-banner__message {
  margin: 0 0 6px 0;
  font-size: 13.5px;
  color: var(--cortex-danger-900, #7f1d1d);
  line-height: 1.4;
}

.cx-error-banner__non-mutation {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 6px 0 0 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--cortex-danger-800, #991b1b);
}

.cx-error-banner__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  font-size: 11.5px;
  color: var(--cortex-text-muted, #436354);
}

.cx-error-banner__meta code {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 11px;
  background-color: rgba(127, 29, 29, 0.08);
  padding: 1px 4px;
  border-radius: 3px;
  color: var(--cortex-danger-900, #7f1d1d);
}

.cx-error-banner__actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.cx-error-banner__dismiss {
  background: transparent;
  border: none;
  color: var(--cortex-danger-700, #b91c1c);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cx-error-banner__dismiss:hover {
  background-color: rgba(185, 28, 28, 0.1);
}
</style>
