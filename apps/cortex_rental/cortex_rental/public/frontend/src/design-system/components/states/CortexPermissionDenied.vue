<script setup lang="ts">
import { computed } from 'vue';
import CortexIcon from '../../icons/CortexIcon.vue';
import CortexButton from '../base/CortexButton.vue';

interface Props {
  requiredRole?: string;
  reason?: string;
  supervisorContact?: string;
  locale?: 'fr-CA' | 'en-CA';
}

const props = withDefaults(defineProps<Props>(), {
  requiredRole: undefined,
  reason: undefined,
  supervisorContact: undefined,
  locale: 'fr-CA',
});

const emit = defineEmits<{
  (e: 'back'): void;
  (e: 'request-access'): void;
}>();

const isFr = computed(() => props.locale === 'fr-CA');

const title = computed(() => {
  return isFr.value ? 'Accès non autorisé' : 'Access Denied';
});

const defaultReason = computed(() => {
  return isFr.value
    ? "Votre rôle utilisateur actuel ne dispose pas des permissions requises pour consulter ou modifier cette ressource."
    : "Your current user role does not possess the required permissions to view or mutate this resource.";
});
</script>

<template>
  <div class="cx-permission-denied" role="alert">
    <div class="cx-permission-denied__icon-wrapper" aria-hidden="true">
      <CortexIcon name="lock" :size="36" color="var(--cortex-amber-900, #78350f)" />
    </div>

    <h3 class="cx-permission-denied__title">{{ title }}</h3>
    <p class="cx-permission-denied__reason">{{ reason || defaultReason }}</p>

    <!-- Required Role Tag -->
    <div v-if="requiredRole" class="cx-permission-denied__role-box">
      <span class="cx-permission-denied__role-label">
        {{ isFr ? 'Rôle RBAC requis :' : 'Required RBAC Role:' }}
      </span>
      <code class="cx-permission-denied__role-code">{{ requiredRole }}</code>
    </div>

    <!-- Supervisor Contact -->
    <p v-if="supervisorContact" class="cx-permission-denied__contact">
      {{ isFr ? 'Pour obtenir un accès, contactez votre superviseur :' : 'To request access, contact your supervisor:' }}
      <a :href="`mailto:${supervisorContact}`" class="cx-permission-denied__link">{{ supervisorContact }}</a>
    </p>

    <!-- Actions -->
    <div class="cx-permission-denied__actions">
      <slot name="actions">
        <CortexButton
          variant="secondary"
          size="md"
          icon="chevron-left"
          @click="emit('back')"
        >
          {{ isFr ? 'Retour à la vue précédente' : 'Back to previous view' }}
        </CortexButton>

        <CortexButton
          variant="primary"
          size="md"
          icon="shield"
          @click="emit('request-access')"
        >
          {{ isFr ? 'Demander une dérogation' : 'Request Exception' }}
        </CortexButton>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.cx-permission-denied {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-12, 48px) var(--space-6, 24px);
  background-color: var(--cortex-surface, #ffffff);
  border: 1px solid var(--cortex-amber-600, #d97706);
  border-radius: var(--radius-md, 8px);
  font-family: var(--font-sans, Inter, sans-serif);
  color: var(--cortex-text, #08120d);
  box-sizing: border-box;
}

.cx-permission-denied__icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: var(--cortex-warning-100, #fef3c7);
  margin-bottom: var(--space-4, 16px);
}

.cx-permission-denied__title {
  margin: 0 0 var(--space-2, 8px) 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--cortex-amber-900, #78350f);
}

.cx-permission-denied__reason {
  margin: 0 0 var(--space-4, 16px) 0;
  font-size: 13.5px;
  color: var(--cortex-text-secondary, #264034);
  max-width: 480px;
  line-height: 1.45;
}

.cx-permission-denied__role-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background-color: var(--cortex-surface-subtle, #f1f5f9);
  border: 1px solid var(--cortex-border, #cbdcd2);
  border-radius: var(--radius-sm, 6px);
  margin-bottom: var(--space-4, 16px);
}

.cx-permission-denied__role-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--cortex-text-muted, #436354);
}

.cx-permission-denied__role-code {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 12.5px;
  font-weight: 700;
  color: var(--cortex-text, #08120d);
}

.cx-permission-denied__contact {
  font-size: 12.5px;
  color: var(--cortex-text-muted, #436354);
  margin: 0 0 var(--space-5, 20px) 0;
}

.cx-permission-denied__link {
  color: var(--cortex-green-600, #087a43);
  font-weight: 600;
  text-decoration: underline;
}

.cx-permission-denied__actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3, 12px);
  flex-wrap: wrap;
}
</style>
