/**
 * Cortex OS — Operational Green Design System
 * Elevation & Shadow Tokens
 */

export const elevation = {
  none: 'none',
  xs: '0 1px 2px rgba(8, 18, 13, 0.04)',
  sm: '0 1px 3px rgba(8, 18, 13, 0.08), 0 1px 2px rgba(8, 18, 13, 0.04)',
  md: '0 4px 12px rgba(8, 18, 13, 0.08), 0 1px 3px rgba(8, 18, 13, 0.05)',
  lg: '0 12px 32px rgba(8, 18, 13, 0.12), 0 2px 6px rgba(8, 18, 13, 0.06)',
  drawer: '-8px 0 24px rgba(8, 18, 13, 0.14)',
} as const;

export type ElevationKey = keyof typeof elevation;
