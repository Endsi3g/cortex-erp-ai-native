<script setup lang="ts">
import { computed } from 'vue';
import CortexIcon, { type IconName } from '../../icons/CortexIcon.vue';

export type ButtonVariant = 'primary' | 'secondary' | 'destructive' | 'ghost' | 'link';
export type ButtonSize = 'sm' | 'md' | 'lg' | 'scanner';

interface Props {
  variant?: ButtonVariant;
  size?: ButtonSize;
  type?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
  loading?: boolean;
  icon?: IconName;
  iconRight?: IconName;
  fullWidth?: boolean;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'secondary',
  size: 'md',
  type: 'button',
  disabled: false,
  loading: false,
  icon: undefined,
  iconRight: undefined,
  fullWidth: false,
  ariaLabel: undefined,
});

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void;
}>();

const iconSize = computed(() => {
  if (props.size === 'sm') return 12;
  if (props.size === 'scanner') return 18;
  if (props.size === 'lg') return 16;
  return 14;
});

function handleClick(e: MouseEvent) {
  if (props.disabled || props.loading) {
    e.preventDefault();
    e.stopPropagation();
    return;
  }
  emit('click', e);
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[
      'cx-btn',
      `cx-btn--${variant}`,
      `cx-btn--${size}`,
      {
        'cx-btn--loading': loading,
        'cx-btn--full-width': fullWidth,
        'cx-btn--icon-only': !$slots.default && (icon || iconRight),
      },
    ]"
    :aria-label="ariaLabel"
    :aria-busy="loading"
    @click="handleClick"
  >
    <!-- Loading Spinner -->
    <span v-if="loading" class="cx-btn__spinner" aria-hidden="true">
      <svg class="cx-btn__spinner-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle class="cx-btn__spinner-track" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
        <path class="cx-btn__spinner-head" d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
      </svg>
    </span>

    <!-- Left Icon -->
    <CortexIcon
      v-if="icon && !loading"
      :name="icon"
      :size="iconSize"
      class="cx-btn__icon cx-btn__icon--left"
    />

    <!-- Button Text / Slot -->
    <span v-if="$slots.default" class="cx-btn__label">
      <slot />
    </span>

    <!-- Right Icon -->
    <CortexIcon
      v-if="iconRight && !loading"
      :name="iconRight"
      :size="iconSize"
      class="cx-btn__icon cx-btn__icon--right"
    />
  </button>
</template>

<style scoped>
.cx-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-sans, Inter, sans-serif);
  font-weight: 600;
  border-radius: var(--radius-md, 8px);
  border-width: 1px;
  border-style: solid;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  vertical-align: middle;
  text-decoration: none;
  transition: all var(--motion-fast, 120ms ease);
  box-sizing: border-box;
}

.cx-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--cortex-surface, #ffffff), 0 0 0 4px var(--focus-ring-color, #087a43);
}

.cx-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  pointer-events: none;
}

.cx-btn--full-width {
  width: 100%;
}

/* Sizes */
.cx-btn--sm {
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  gap: 5px;
  border-radius: var(--radius-sm, 6px);
}

/* Sm size touch target expansion for mobile */
@media (max-width: 768px) {
  .cx-btn--sm::after {
    content: '';
    position: absolute;
    top: -8px;
    bottom: -8px;
    left: -8px;
    right: -8px;
  }
}

.cx-btn--md {
  height: 36px;
  padding: 0 14px;
  font-size: 13.5px;
  gap: 6px;
}

.cx-btn--lg {
  height: 44px;
  padding: 0 20px;
  font-size: 14.5px;
  gap: 8px;
}

.cx-btn--scanner {
  height: 52px;
  padding: 0 24px;
  font-size: 16px;
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-weight: 700;
  gap: 10px;
  letter-spacing: 0.02em;
}

/* Variants */
.cx-btn--primary {
  background-color: var(--cortex-green-600, #087a43);
  color: #ffffff;
  border-color: var(--cortex-green-700, #065f34);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(8, 18, 13, 0.04));
}

.cx-btn--primary:hover:not(:disabled) {
  background-color: var(--cortex-green-700, #065f34);
  border-color: var(--cortex-green-800, #044727);
}

.cx-btn--primary:active:not(:disabled) {
  background-color: var(--cortex-green-800, #044727);
}

.cx-btn--secondary {
  background-color: var(--cortex-surface, #ffffff);
  color: var(--cortex-text, #08120d);
  border-color: var(--cortex-border, #cbdcd2);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(8, 18, 13, 0.04));
}

.cx-btn--secondary:hover:not(:disabled) {
  background-color: var(--cortex-surface-hover, #e3ece6);
  border-color: var(--cortex-border-strong, #182c24);
}

.cx-btn--secondary:active:not(:disabled) {
  background-color: var(--cortex-ink-100, #e3ece6);
}

.cx-btn--destructive {
  background-color: var(--cortex-surface, #ffffff);
  color: var(--cortex-danger-700, #b91c1c);
  border-color: var(--cortex-danger-600, #dc2626);
}

.cx-btn--destructive:hover:not(:disabled) {
  background-color: var(--cortex-danger-50, #fef2f2);
  color: var(--cortex-danger-900, #7f1d1d);
  border-color: var(--cortex-danger-700, #b91c1c);
}

.cx-btn--destructive:active:not(:disabled) {
  background-color: var(--cortex-danger-100, #fee2e2);
}

.cx-btn--ghost {
  background-color: transparent;
  color: var(--cortex-text-secondary, #264034);
  border-color: transparent;
}

.cx-btn--ghost:hover:not(:disabled) {
  background-color: var(--cortex-surface-hover, #e3ece6);
  color: var(--cortex-text, #08120d);
}

.cx-btn--ghost:active:not(:disabled) {
  background-color: var(--cortex-ink-100, #e3ece6);
}

.cx-btn--link {
  background-color: transparent;
  color: var(--cortex-green-600, #087a43);
  border-color: transparent;
  padding-left: 0;
  padding-right: 0;
  height: auto;
}

.cx-btn--link:hover:not(:disabled) {
  color: var(--cortex-green-800, #044727);
  text-decoration: underline;
}

/* Spinner */
.cx-btn__spinner {
  display: inline-flex;
  align-items: center;
  margin-right: 6px;
}

.cx-btn__spinner-svg {
  width: 14px;
  height: 14px;
  animation: cx-spin 0.8s linear infinite;
}

.cx-btn__spinner-track {
  opacity: 0.25;
}

.cx-btn__spinner-head {
  opacity: 0.9;
}

@keyframes cx-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
