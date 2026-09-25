/**
 * Cortex OS — Operational Green Design System
 * Typography Tokens & Scale
 * 
 * Rules:
 * - `Inter` for operational UI, forms, tables, buttons, and navigation.
 * - `JetBrains Mono` strictly for IDs, serial numbers, audit hashes, monetary values, and codes.
 */

export const typography = {
  fontFamily: {
    sans: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
  },

  fontSize: {
    '2xs': '10px',
    xs: '11px',
    sm: '12px',
    base: '13.5px', // Standard operational body size
    md: '14px',
    lg: '15px',     // Card titles
    xl: '17px',
    '2xl': '19px',   // Section headers
    '3xl': '22px',
    '4xl': '26px',   // Page titles
    kpi: '32px',    // KPI numbers
  },

  fontWeight: {
    regular: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },

  lineHeight: {
    none: '1',
    tight: '1.2',
    snug: '1.3',
    normal: '1.4',
    relaxed: '1.5',
    loose: '1.75',
  },

  letterSpacing: {
    tighter: '-0.025em',
    tight: '-0.015em',
    normal: '0em',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  },

  // Operational Type Scales
  scales: {
    pageTitle: {
      fontFamily: 'sans',
      fontSize: '26px',
      lineHeight: '1.25',
      fontWeight: '700',
      letterSpacing: '-0.015em',
    },
    sectionTitle: {
      fontFamily: 'sans',
      fontSize: '19px',
      lineHeight: '1.30',
      fontWeight: '600',
      letterSpacing: '-0.01em',
    },
    cardTitle: {
      fontFamily: 'sans',
      fontSize: '15px',
      lineHeight: '1.35',
      fontWeight: '600',
      letterSpacing: '-0.005em',
    },
    body: {
      fontFamily: 'sans',
      fontSize: '13.5px',
      lineHeight: '1.45',
      fontWeight: '400',
      letterSpacing: '0em',
    },
    label: {
      fontFamily: 'sans',
      fontSize: '12px',
      lineHeight: '1.30',
      fontWeight: '600',
      letterSpacing: '0.04em',
      textTransform: 'uppercase' as const,
    },
    tableData: {
      fontFamily: 'sans',
      fontSize: '13px',
      lineHeight: '1.40',
      fontWeight: '500',
      letterSpacing: '0em',
    },
    technicalMono: {
      fontFamily: 'mono',
      fontSize: '12.5px',
      lineHeight: '1.40',
      fontWeight: '500',
      letterSpacing: '0em',
    },
    kpiFigure: {
      fontFamily: 'sans',
      fontSize: '32px',
      lineHeight: '1.15',
      fontWeight: '700',
      letterSpacing: '-0.02em',
      fontVariantNumeric: 'tabular-nums',
    },
  },
} as const;

/**
 * Format currency according to CAD standards:
 * fr-CA: 1 920,00 $
 * en-CA: $1,920.00
 */
export function formatCurrencyCad(amount: number, locale: 'fr-CA' | 'en-CA' = 'fr-CA'): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'CAD',
    currencyDisplay: 'symbol',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}
