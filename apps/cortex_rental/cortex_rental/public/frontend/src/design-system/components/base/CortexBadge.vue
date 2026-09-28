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
    <!-- Status dot: the colour carries the meaning, the text always states it too -->
    <span v-if="dot || isStateKey || variant !== 'neutral'" class="cx-badge__dot" aria-hidden="true" />
    <CortexIcon v-else-if="resolvedIcon" :name="resolvedIcon" :size="iconSize" class="cx-badge__icon" />

    <!-- Badge Text -->
    <span class="cx-badge__text">{{ resolvedLabel }}</span>
  </span>
</template>

<style scoped>
/* One flat tag; only the small dot changes colour (green = done/ok, amber = attention, red = blocked, grey = neutral). */
.cx-badge {
  --cx-dot: #7c7c7c;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
  min-height: 22px;
  border: 0;
  border-radius: 6px;
  background-color: #f3f3f3;
  color: #171717;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.2;
  white-space: nowrap;
  vertical-align: middle;
  user-select: none;
  box-sizing: border-box;
}

.cx-badge--sm { min-height: 20px; padding: 0 6px; font-size: 12px; }
.cx-badge--lg { min-height: 26px; padding: 0 10px; font-size: 13px; }

.cx-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--cx-dot);
  flex-shrink: 0;
}

.cx-badge--contract,
.cx-badge--checked_out,
.cx-badge--returned,
.cx-badge--invoiced,
.cx-badge--success { --cx-dot: #087a43; }

.cx-badge--reservation,
.cx-badge--partial_return,
.cx-badge--invoice_prepared,
.cx-badge--repair,
.cx-badge--warning { --cx-dot: #d97706; }

.cx-badge--disputed,
.cx-badge--quarantine,
.cx-badge--missing,
.cx-badge--conflict,
.cx-badge--danger { --cx-dot: #dc2626; }
</style>
