/**
 * Cortex OS — Operational Green Design System
 * Border Radius Tokens
 */

export const radius = {
  none: '0px',
  xs: '4px',
  sm: '6px',     // Inputs, badges, small buttons, tooltips
  md: '8px',     // Cards, tables, standard buttons, dropdown menus
  lg: '12px',    // Modals, Copilot drawer, elevated panels
  xl: '16px',    // Dialogs, onboarding cards
  pill: '9999px', // Status tags, filter chips, avatar containers
} as const;

export type RadiusKey = keyof typeof radius;
