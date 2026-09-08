<script setup lang="ts">
import { computed } from 'vue';
import { aiStateTokens, type AiStateType } from '../../tokens/colors';
import CortexIcon, { type IconName } from '../../icons/CortexIcon.vue';

interface Props {
  state: AiStateType;
  locale?: 'fr-CA' | 'en-CA';
  size?: 'sm' | 'md' | 'lg';
  isDemo?: boolean;
  confidence?: number;
  customLabel?: string;
  clickable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  locale: 'fr-CA',
  size: 'md',
  isDemo: false,
  confidence: undefined,
  customLabel: undefined,
  clickable: false,
});

const emit = defineEmits<{
  (e: 'click', event: MouseEvent | KeyboardEvent): void;
  (e: 'view-proof'): void;
}>();

const config = computed(() => aiStateTokens[props.state] || aiStateTokens.verified);

const label = computed(() => {
  if (props.customLabel) return props.customLabel;
  return props.locale === 'en-CA' ? config.value.labelEn : config.value.labelFr;
});

const formattedConfidence = computed(() => {
  if (props.confidence === undefined) return null;
  const val = props.confidence <= 1 ? Math.round(props.confidence * 100) : Math.round(props.confidence);
  return `${val}%`;
});

const iconSize = computed(() => {
  if (props.size === 'sm') return 12;
  if (props.size === 'lg') return 16;
  return 14;
});

function handleClick(e: MouseEvent | KeyboardEvent) {
  if (props.clickable) {
    emit('click', e);
  }
}
</script>

<template>
  <span
    :class="[
      'cx-ai-badge',
      `cx-ai-badge--${state}`,
      `cx-ai-badge--${size}`,
      { 'cx-ai-badge--clickable': clickable },
    ]"
    :style="{
      backgroundColor: config.fill,
      color: config.text,
      borderColor: config.border,
      borderStyle: config.borderStyle,
    }"
    :role="clickable ? 'button' : 'status'"
    :tabindex="clickable ? 0 : undefined"
    @click="handleClick"
    @keydown.enter="handleClick"
  >
    <!-- State SVG Icon (Triple Encoding Part 1: Shape & Glyph) -->
    <CortexIcon
      :name="config.icon as IconName"
      :size="iconSize"
      :color="config.text"
      class="cx-ai-badge__icon"
    />

    <!-- Localized Text Label (Triple Encoding Part 2: Explicit Text) -->
    <span class="cx-ai-badge__label">{{ label }}</span>

    <!-- Optional Confidence Pill (for 'extracted') -->
    <span v-if="state === 'extracted' && formattedConfidence" class="cx-ai-badge__confidence">
      {{ formattedConfidence }}
    </span>

    <!-- DEMO tag when data is synthetic mock -->
    <span v-if="isDemo" class="cx-ai-badge__demo">
      DEMO
    </span>
  </span>
</template>

<style scoped>
.cx-ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-sans, Inter, sans-serif);
  font-weight: 600;
  border-width: 1px;
  border-radius: var(--radius-sm, 6px);
  line-height: 1.2;
  white-space: nowrap;
  vertical-align: middle;
  user-select: none;
  box-sizing: border-box;
}

/* Sizes */
.cx-ai-badge--sm {
  padding: 2px 6px;
  font-size: 11px;
  gap: 4px;
}

.cx-ai-badge--md {
  padding: 4px 8px;
  font-size: 12px;
  gap: 6px;
}

.cx-ai-badge--lg {
  padding: 6px 12px;
  font-size: 13px;
  gap: 8px;
}

.cx-ai-badge--clickable {
  cursor: pointer;
  transition: opacity var(--motion-fast, 120ms ease);
}

.cx-ai-badge--clickable:hover {
  opacity: 0.9;
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(8, 18, 13, 0.04));
}

.cx-ai-badge--clickable:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--cortex-surface, #ffffff), 0 0 0 4px var(--focus-ring-color, #087a43);
}

.cx-ai-badge__icon {
  flex-shrink: 0;
}

.cx-ai-badge__label {
  letter-spacing: 0.01em;
}

.cx-ai-badge__confidence {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 0.85em;
  font-weight: 700;
  padding: 1px 4px;
  background-color: rgba(91, 33, 182, 0.12);
  border-radius: 4px;
}

.cx-ai-badge__demo {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 10px;
  font-weight: 700;
  padding: 0 4px;
  background-color: rgba(8, 18, 13, 0.15);
  border-radius: 3px;
  letter-spacing: 0.05em;
}
</style>
