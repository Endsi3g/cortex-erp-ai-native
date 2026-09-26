<script setup lang="ts">
import { computed } from 'vue';

export type SkeletonVariant = 'text' | 'circle' | 'rect' | 'card' | 'table-row';

interface Props {
  variant?: SkeletonVariant;
  width?: string;
  height?: string;
  borderRadius?: string;
  count?: number;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'text',
  width: undefined,
  height: undefined,
  borderRadius: undefined,
  count: 1,
  ariaLabel: 'Chargement en cours...',
});

const defaultHeight = computed(() => {
  switch (props.variant) {
    case 'text':
      return '16px';
    case 'circle':
      return props.width || '40px';
    case 'rect':
      return '80px';
    case 'card':
      return '160px';
    case 'table-row':
      return '38px';
    default:
      return '16px';
  }
});
</script>

<template>
  <div
    class="cx-skeleton-wrapper"
    role="status"
    aria-live="polite"
    :aria-label="ariaLabel"
  >
    <div
      v-for="n in count"
      :key="n"
      :class="[
        'cx-skeleton',
        `cx-skeleton--${variant}`,
      ]"
      :style="{
        width: width,
        height: height || defaultHeight,
        borderRadius: borderRadius,
      }"
    />
  </div>
</template>

<style scoped>
.cx-skeleton-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.cx-skeleton {
  background: linear-gradient(
    90deg,
    var(--cortex-surface-subtle, #f1f5f9) 25%,
    var(--cortex-border, #cbdcd2) 50%,
    var(--cortex-surface-subtle, #f1f5f9) 75%
  );
  background-size: 200% 100%;
  animation: cx-shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm, 6px);
  width: 100%;
  box-sizing: border-box;
}

.cx-skeleton--circle {
  border-radius: 50% !important;
  width: 40px;
}

.cx-skeleton--text {
  border-radius: 4px;
}

.cx-skeleton--card {
  border-radius: var(--radius-md, 8px);
}

.cx-skeleton--table-row {
  border-radius: 4px;
}

@keyframes cx-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
