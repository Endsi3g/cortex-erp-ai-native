<script setup lang="ts">
import { computed } from 'vue';
import CortexIcon, { type IconName } from '../../icons/CortexIcon.vue';
import CortexButton from '../base/CortexButton.vue';

interface Props {
  icon?: IconName;
  title?: string;
  description?: string;
  actionText?: string;
  actionIcon?: IconName;
  secondaryActionText?: string;
  locale?: 'fr-CA' | 'en-CA';
}

const props = withDefaults(defineProps<Props>(), {
  icon: 'archive',
  title: undefined,
  description: undefined,
  actionText: undefined,
  actionIcon: undefined,
  secondaryActionText: undefined,
  locale: 'fr-CA',
});

const emit = defineEmits<{
  (e: 'action'): void;
  (e: 'secondary-action'): void;
}>();

const isFr = computed(() => props.locale === 'fr-CA');

const resolvedTitle = computed(() => {
  if (props.title) return props.title;
  return isFr.value ? 'Aucun élément trouvé' : 'No items found';
});

const resolvedDescription = computed(() => {
  if (props.description) return props.description;
  return isFr.value
    ? 'Il n’y a aucun enregistrement correspondant à vos critères de recherche ou filtres actuels.'
    : 'There are no records matching your search criteria or active filters.';
});
</script>

<template>
  <div class="cx-empty-state" role="status">
    <div class="cx-empty-state__icon-wrapper" aria-hidden="true">
      <CortexIcon
        :name="icon"
        :size="36"
        color="var(--cortex-text-muted, #436354)"
      />
    </div>

    <h3 class="cx-empty-state__title">{{ resolvedTitle }}</h3>
    <p class="cx-empty-state__description">{{ resolvedDescription }}</p>

    <!-- Actions -->
    <div v-if="$slots.actions || actionText || secondaryActionText" class="cx-empty-state__actions">
      <slot name="actions">
        <CortexButton
          v-if="actionText"
          variant="primary"
          size="md"
          :icon="actionIcon"
          @click="emit('action')"
        >
          {{ actionText }}
        </CortexButton>

        <CortexButton
          v-if="secondaryActionText"
          variant="secondary"
          size="md"
          @click="emit('secondary-action')"
        >
          {{ secondaryActionText }}
        </CortexButton>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.cx-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-12, 48px) var(--space-6, 24px);
  background-color: var(--cortex-surface, #ffffff);
  border: 1px dashed var(--cortex-border, #cbdcd2);
  border-radius: var(--radius-md, 8px);
  font-family: var(--font-sans, Inter, sans-serif);
  color: var(--cortex-text, #08120d);
  box-sizing: border-box;
}

.cx-empty-state__icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: var(--cortex-surface-subtle, #f1f5f9);
  margin-bottom: var(--space-4, 16px);
}

.cx-empty-state__title {
  margin: 0 0 var(--space-2, 8px) 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--cortex-text, #08120d);
}

.cx-empty-state__description {
  margin: 0 0 var(--space-5, 20px) 0;
  font-size: 13.5px;
  color: var(--cortex-text-muted, #436354);
  max-width: 440px;
  line-height: 1.45;
}

.cx-empty-state__actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3, 12px);
  flex-wrap: wrap;
}
</style>
