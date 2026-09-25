<script setup lang="ts">
import { computed } from 'vue';
import CortexIcon from '../../icons/CortexIcon.vue';
import CortexButton from '../base/CortexButton.vue';

interface Props {
  lastSyncedAt?: string;
  message?: string;
  loading?: boolean;
  locale?: 'fr-CA' | 'en-CA';
}

const props = withDefaults(defineProps<Props>(), {
  lastSyncedAt: undefined,
  message: undefined,
  loading: false,
  locale: 'fr-CA',
});

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const isFr = computed(() => props.locale === 'fr-CA');

const defaultMessage = computed(() => {
  return isFr.value
    ? 'Les disponibilités ou données ont été modifiées par un autre utilisateur ou événement système.'
    : 'Availability or records have been updated by another user or system event.';
});
</script>

<template>
  <div class="cx-stale-notice" role="status" aria-live="polite">
    <div class="cx-stale-notice__main">
      <CortexIcon
        name="alert-triangle"
        :size="18"
        color="var(--cortex-warning-800, #92400e)"
        class="cx-stale-notice__icon"
      />
      <div class="cx-stale-notice__text">
        <strong class="cx-stale-notice__title">
          {{ isFr ? 'Données potentiellement obsolètes' : 'Potentially stale data' }}
        </strong>
        <p class="cx-stale-notice__desc">{{ message || defaultMessage }}</p>
        <span v-if="lastSyncedAt" class="cx-stale-notice__timestamp">
          {{ isFr ? 'Dernière synchro :' : 'Last sync:' }} {{ lastSyncedAt }}
        </span>
      </div>
    </div>

    <CortexButton
      variant="secondary"
      size="sm"
      icon="refresh-cw"
      :loading="loading"
      @click="emit('refresh')"
    >
      {{ isFr ? 'Actualiser la vue' : 'Refresh view' }}
    </CortexButton>
  </div>
</template>

<style scoped>
.cx-stale-notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3, 12px);
  padding: var(--space-3, 12px) var(--space-4, 16px);
  background-color: var(--cortex-warning-50, #fffbeb);
  border: 1px solid var(--cortex-warning-500, #f59e0b);
  border-radius: var(--radius-md, 8px);
  font-family: var(--font-sans, Inter, sans-serif);
  color: var(--cortex-warning-900, #78350f);
  margin-bottom: var(--space-4, 16px);
  box-sizing: border-box;
  flex-wrap: wrap;
}

.cx-stale-notice__main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex-grow: 1;
}

.cx-stale-notice__icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.cx-stale-notice__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cx-stale-notice__title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--cortex-warning-900, #78350f);
}

.cx-stale-notice__desc {
  margin: 0;
  font-size: 12.5px;
  color: var(--cortex-warning-800, #92400e);
}

.cx-stale-notice__timestamp {
  font-size: 11px;
  color: var(--cortex-text-muted, #436354);
  margin-top: 2px;
}
</style>
