/**
 * Cortex OS — Operational Green Design System
 * Spacing Tokens (4px base grid)
 */

export const spacing = {
  0: '0px',
  1: '4px',   // Micro gap, icon-to-label spacing
  2: '8px',   // Button padding-x, input padding-y, badge gap
  3: '12px',  // Compact padding, form row gap
  4: '16px',  // Standard padding, container gap
  5: '20px',  // Modal header padding, section padding
  6: '24px',  // Page layout padding, drawer padding
  8: '32px',  // Page header bottom margin, major sections
  10: '40px', // Large hero section gap
  12: '48px', // Empty state container spacing
  16: '64px', // Bottom bar height mobile, scanner footer
} as const;

export type SpacingKey = keyof typeof spacing;
