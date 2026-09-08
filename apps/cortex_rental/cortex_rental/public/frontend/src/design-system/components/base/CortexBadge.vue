<script setup lang="ts">
import { computed } from 'vue';
import { operationalStateTokens, type OperationalStateType } from '../../tokens/colors';
import CortexIcon, { type IconName } from '../../icons/CortexIcon.vue';

export type BadgeVariant = OperationalStateType | 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'violet';
export type BadgeSize = 'sm' | 'md' | 'lg';

interface Props {
  variant?: BadgeVariant;
  size?: BadgeSize;
  label?: string;
  icon?: IconName;
  dot?: boolean;
  locale?: 'fr-CA' | 'en-CA';
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'neutral',
  size: 'md',
  label: undefined,
  icon: undefined,
  dot: false,
  locale: 'fr-CA',
});

const isStateKey = computed(() => props.variant in operationalStateTokens);

const stateConfig = computed(() => {
  if (isStateKey.value) {
    return operationalStateTokens[props.variant as OperationalStateType];
  }
  return null;
});

const resolvedLabel = computed(() => {
  if (props.label) return props.label;
  if (stateConfig.value) {
    return props.locale === 'en-CA' ? stateConfig.value.labelEn : stateConfig.value.labelFr;
  }
  return props.variant;
});

const resolvedIcon = computed<IconName | undefined>(() => {
  if (props.icon) return props.icon;
  if (stateConfig.value && !props.dot) {
    return stateConfig.value.icon as IconName;
  }
  return undefined;
});

const iconSize = computed(() => {
  if (props.size === 'sm') return 11;
  if (props.size === 'lg') return 15;
  return 13;
});
</script>

<template>
  <span
    :class="[
      'cx-badge',
      `cx-badge--${variant}`,
      `cx-badge--${size}`,
      { 'cx-badge--has-dot': dot },
    ]"
    role="status"
  >
    <!-- Dot Indicator -->
    <span v-if="dot" class="cx-badge__dot" aria-hidden="true" />

    <!-- Icon -->
    <CortexIcon
      v-else-if="resolvedIcon"
      :name="resolvedIcon"
      :size="iconSize"
      class="cx-badge__icon"
    />

    <!-- Badge Text -->
    <span class="cx-badge__text">{{ resolvedLabel }}</span>
  </span>
</template>

<style scoped>
.cx-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-sans, Inter, sans-serif);
  font-weight: 600;
  border-radius: var(--radius-sm, 6px);
  border-width: 1px;
  border-style: solid;
  line-height: 1.2;
  white-space: nowrap;
  vertical-align: middle;
  user-select: none;
  box-sizing: border-box;
}

/* Sizes */
.cx-badge--sm {
  padding: 2px 6px;
  font-size: 11px;
  gap: 4px;
}

.cx-badge--md {
  padding: 3px 8px;
  font-size: 12px;
  gap: 5px;
}

.cx-badge--lg {
  padding: 5px 10px;
  font-size: 13px;
  gap: 6px;
}

/* Dot Indicator */
.cx-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
  flex-shrink: 0;
}

/* Operational States */
.cx-badge--quote {
  background-color: var(--state-quote-bg, #f1f5f9);
  color: var(--state-quote-text, #334155);
  border-color: var(--state-quote-border, #64748b);
}

.cx-badge--draft {
  background-color: var(--state-draft-bg, #f1f5f9);
  color: var(--state-draft-text, #475569);
  border-color: var(--state-draft-border, #64748b);
}

.cx-badge--reservation {
  background-color: var(--state-reservation-bg, #fffbeb);
  color: var(--state-reservation-text, #92400e);
  border-color: var(--state-reservation-border, #b45309);
}

.cx-badge--contract {
  background-color: var(--state-contract-bg, #eff6ff);
  color: var(--state-contract-text, #1d4ed8);
  border-color: var(--state-contract-border, #3b82f6);
}

.cx-badge--checked_out {
  background-color: var(--state-checked-out-bg, #f5f3ff);
  color: var(--state-checked-out-text, #6d28d9);
  border-color: var(--state-checked-out-border, #8b5cf6);
}

.cx-badge--partial_return {
  background-color: var(--state-partial-return-bg, #ecfeff);
  color: var(--state-partial-return-text, #0e7490);
  border-color: var(--state-partial-return-border, #0891b2);
}

.cx-badge--returned {
  background-color: var(--state-returned-bg, #ecfdf5);
  color: var(--state-returned-text, #047857);
  border-color: var(--state-returned-border, #059669);
}

.cx-badge--invoice_prepared {
  background-color: var(--state-invoice-prepared-bg, #eff6ff);
  color: var(--state-invoice-prepared-text, #1d4ed8);
  border-color: var(--state-invoice-prepared-border, #3b82f6);
}

.cx-badge--invoiced {
  background-color: var(--state-invoiced-bg, #ecfdf5);
  color: var(--state-invoiced-text, #047857);
  border-color: var(--state-invoiced-border, #059669);
}

.cx-badge--closed {
  background-color: var(--state-closed-bg, #f1f5f9);
  color: var(--state-closed-text, #475569);
  border-color: var(--state-closed-border, #64748b);
}

.cx-badge--cancelled {
  background-color: var(--state-cancelled-bg, #f1f5f9);
  color: var(--state-cancelled-text, #475569);
  border-color: var(--state-cancelled-border, #64748b);
}

.cx-badge--disputed {
  background-color: var(--state-disputed-bg, #fef2f2);
  color: var(--state-disputed-text, #b91c1c);
  border-color: var(--state-disputed-border, #ef4444);
}

.cx-badge--conflict {
  background-color: var(--state-conflict-bg, #fef2f2);
  color: var(--state-conflict-text, #b91c1c);
  border-color: var(--state-conflict-border, #ef4444);
}

.cx-badge--quarantine {
  background-color: var(--state-quarantine-bg, #fff7ed);
  color: var(--state-quarantine-text, #c2410c);
  border-color: var(--state-quarantine-border, #ea580c);
}

.cx-badge--repair {
  background-color: var(--state-repair-bg, #fff1f2);
  color: var(--state-repair-text, #be123c);
  border-color: var(--state-repair-border, #f43f5e);
}

.cx-badge--missing {
  background-color: var(--state-missing-bg, #fef2f2);
  color: var(--state-missing-text, #991b1b);
  border-color: var(--state-missing-border, #dc2626);
}

/* Generic Semantic Variants */
.cx-badge--neutral {
  background-color: var(--cortex-surface-subtle, #f1f5f9);
  color: var(--cortex-text-secondary, #264034);
  border-color: var(--cortex-border, #cbdcd2);
}

.cx-badge--success {
  background-color: var(--cortex-green-50, #edfbf2);
  color: var(--cortex-green-800, #044727);
  border-color: var(--cortex-green-600, #087a43);
}

.cx-badge--warning {
  background-color: var(--cortex-warning-100, #fef3c7);
  color: var(--cortex-warning-900, #78350f);
  border-color: var(--cortex-warning-700, #b45309);
}

.cx-badge--danger {
  background-color: var(--cortex-danger-100, #fee2e2);
  color: var(--cortex-danger-900, #7f1d1d);
  border-color: var(--cortex-danger-600, #dc2626);
}

.cx-badge--info {
  background-color: var(--cortex-info-100, #dbeafe);
  color: var(--cortex-info-900, #1e3a8a);
  border-color: var(--cortex-info-600, #2563eb);
}

.cx-badge--violet {
  background-color: var(--cortex-violet-100, #ede9fe);
  color: var(--cortex-violet-800, #5b21b6);
  border-color: var(--cortex-violet-600, #7c3aed);
}
</style>
