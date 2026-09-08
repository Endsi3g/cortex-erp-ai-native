<script setup lang="ts">
import { computed } from 'vue';

export type StatusColor = 'green' | 'amber' | 'red' | 'blue' | 'violet' | 'gray';
export type IndicatorSize = 'sm' | 'md' | 'lg';

interface Props {
  status?: StatusColor;
  size?: IndicatorSize;
  pulse?: boolean;
  label?: string;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  status: 'green',
  size: 'md',
  pulse: false,
  label: undefined,
  ariaLabel: undefined,
});

const colorMap = {
  green: {
    bg: 'var(--cortex-green-500, #087a43)',
    pulse: 'var(--cortex-green-400, #14b86a)',
  },
  amber: {
    bg: 'var(--cortex-warning-600, #d97706)',
    pulse: 'var(--cortex-warning-500, #f59e0b)',
  },
  red: {
    bg: 'var(--cortex-danger-600, #dc2626)',
    pulse: 'var(--cortex-danger-500, #ef4444)',
  },
  blue: {
    bg: 'var(--cortex-info-600, #2563eb)',
    pulse: 'var(--cortex-info-500, #3b82f6)',
  },
  violet: {
    bg: 'var(--cortex-violet-600, #7c3aed)',
    pulse: 'var(--cortex-violet-500, #8b5cf6)',
  },
  gray: {
    bg: 'var(--cortex-text-muted, #436354)',
    pulse: 'var(--cortex-text-disabled, #6d9685)',
  },
};

const currentColor = computed(() => colorMap[props.status] || colorMap.green);
</script>

<template>
  <span class="cx-status-indicator" role="status" :aria-label="ariaLabel || label">
    <span :class="['cx-status-indicator__dot-wrapper', `cx-status-indicator--${size}`]">
      <span
        v-if="pulse"
        class="cx-status-indicator__pulse"
        :style="{ backgroundColor: currentColor.pulse }"
        aria-hidden="true"
      />
      <span
        class="cx-status-indicator__dot"
        :style="{ backgroundColor: currentColor.bg }"
        aria-hidden="true"
      />
    </span>
    <span v-if="label" class="cx-status-indicator__label">{{ label }}</span>
  </span>
</template>

<style scoped>
.cx-status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-sans, Inter, sans-serif);
  font-size: 12.5px;
  color: var(--cortex-text, #08120d);
  vertical-align: middle;
}

.cx-status-indicator__dot-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Sizes */
.cx-status-indicator--sm {
  width: 8px;
  height: 8px;
}
.cx-status-indicator--sm .cx-status-indicator__dot {
  width: 6px;
  height: 6px;
}

.cx-status-indicator--md {
  width: 12px;
  height: 12px;
}
.cx-status-indicator--md .cx-status-indicator__dot {
  width: 8px;
  height: 8px;
}

.cx-status-indicator--lg {
  width: 16px;
  height: 16px;
}
.cx-status-indicator--lg .cx-status-indicator__dot {
  width: 10px;
  height: 10px;
}

.cx-status-indicator__dot {
  border-radius: 50%;
  display: block;
}

.cx-status-indicator__pulse {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  opacity: 0.75;
  animation: cx-ping 1.6s cubic-bezier(0, 0, 0.2, 1) infinite;
}

.cx-status-indicator__label {
  font-weight: 500;
  letter-spacing: 0.01em;
}

@keyframes cx-ping {
  75%, 100% {
    transform: scale(2);
    opacity: 0;
  }
}
</style>
