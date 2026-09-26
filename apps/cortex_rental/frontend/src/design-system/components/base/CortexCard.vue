<script setup lang="ts">
import { computed } from 'vue';

export type CardVariant = 'default' | 'elevated' | 'interactive' | 'ai-proposed' | 'conflict-alert';
export type CardDensity = 'comfortable' | 'compact';

interface Props {
  variant?: CardVariant;
  density?: CardDensity;
  title?: string;
  subtitle?: string;
  clickable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  density: 'comfortable',
  title: undefined,
  subtitle: undefined,
  clickable: false,
});

const emit = defineEmits<{
  (e: 'click', event: MouseEvent | KeyboardEvent): void;
}>();

const isClickable = computed(() => props.clickable || props.variant === 'interactive');

function handleClick(e: MouseEvent | KeyboardEvent) {
  if (isClickable.value) {
    emit('click', e);
  }
}
</script>

<template>
  <div
    :class="[
      'cx-card',
      `cx-card--${variant}`,
      `cx-card--${density}`,
      { 'cx-card--clickable': isClickable },
    ]"
    :tabindex="isClickable ? 0 : undefined"
    :role="isClickable ? 'button' : undefined"
    @click="handleClick"
    @keydown.enter="handleClick"
  >
    <!-- Card Header -->
    <header v-if="title || $slots.header || $slots.actions" class="cx-card__header">
      <slot name="header">
        <div class="cx-card__heading">
          <h3 v-if="title" class="cx-card__title">{{ title }}</h3>
          <p v-if="subtitle" class="cx-card__subtitle">{{ subtitle }}</p>
        </div>
      </slot>
      <div v-if="$slots.actions" class="cx-card__actions">
        <slot name="actions" />
      </div>
    </header>

    <!-- Card Content / Default Slot -->
    <div class="cx-card__body">
      <slot />
    </div>

    <!-- Card Footer -->
    <footer v-if="$slots.footer" class="cx-card__footer">
      <slot name="footer" />
    </footer>
  </div>
</template>

<style scoped>
.cx-card {
  background-color: var(--cortex-surface, #ffffff);
  border: 1px solid var(--cortex-border, #cbdcd2);
  border-radius: var(--radius-md, 8px);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(8, 18, 13, 0.04));
  font-family: var(--font-sans, Inter, sans-serif);
  color: var(--cortex-text, #08120d);
  box-sizing: border-box;
  transition: all var(--motion-fast, 120ms ease);
}

/* Densities */
.cx-card--comfortable {
  padding: var(--space-5, 20px);
}

.cx-card--compact {
  padding: var(--space-3, 12px);
}

/* Variants */
.cx-card--elevated {
  box-shadow: var(--shadow-md, 0 4px 12px rgba(8, 18, 13, 0.08));
}

.cx-card--interactive {
  cursor: pointer;
}

.cx-card--interactive:hover {
  border-color: var(--cortex-border-strong, #182c24);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(8, 18, 13, 0.08));
}

.cx-card--ai-proposed {
  border: 1.5px dashed var(--cortex-green-600, #087a43);
  background-color: var(--cortex-green-50, #edfbf2);
}

.cx-card--conflict-alert {
  border: 2px solid var(--cortex-danger-600, #dc2626);
  background-color: var(--cortex-danger-50, #fef2f2);
}

.cx-card--clickable {
  cursor: pointer;
}

.cx-card--clickable:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--cortex-surface, #ffffff), 0 0 0 4px var(--focus-ring-color, #087a43);
}

/* Card Sub-elements */
.cx-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3, 12px);
  margin-bottom: var(--space-3, 12px);
  flex-wrap: wrap;
}

.cx-card__heading {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cx-card__title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.005em;
  color: var(--cortex-text, #08120d);
}

.cx-card__subtitle {
  margin: 0;
  font-size: 12.5px;
  color: var(--cortex-text-muted, #436354);
}

.cx-card__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
}

.cx-card__body {
  font-size: 13.5px;
  color: var(--cortex-text-secondary, #264034);
  line-height: 1.45;
}

.cx-card__footer {
  margin-top: var(--space-4, 16px);
  padding-top: var(--space-3, 12px);
  border-top: 1px solid var(--cortex-border, #cbdcd2);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2, 8px);
}
</style>
