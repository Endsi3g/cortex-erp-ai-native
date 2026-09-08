/**
 * Cortex OS — Operational Green Design System
 * Motion & Animation Tokens
 * 
 * Rules:
 * - Micro-interactions: 120ms (fast)
 * - Standard transitions: 180ms (base)
 * - Major panel & modal transitions: 240ms (slow)
 * - All suppressed when prefers-reduced-motion is active
 */

export const motion = {
  duration: {
    fast: '120ms',
    base: '180ms',
    slow: '240ms',
    reduced: '0.001ms',
  },

  easing: {
    standard: 'cubic-bezier(0.16, 1, 0.3, 1)',
    decelerate: 'cubic-bezier(0, 0, 0.2, 1)',
    accelerate: 'cubic-bezier(0.4, 0, 1, 1)',
  },

  transition: {
    fast: '120ms cubic-bezier(0.16, 1, 0.3, 1)',
    base: '180ms cubic-bezier(0.16, 1, 0.3, 1)',
    slow: '240ms cubic-bezier(0.16, 1, 0.3, 1)',
    reduced: '0.001ms !important',
  },
} as const;

export type MotionDurationKey = keyof typeof motion.duration;
