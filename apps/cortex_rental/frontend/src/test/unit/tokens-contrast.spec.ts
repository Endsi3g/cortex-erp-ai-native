import { describe, it, expect } from 'vitest'

// Helper function to calculate relative luminance of sRGB color
function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '')
  const bigint = parseInt(clean, 16)
  const r = (bigint >> 16) & 255
  const g = (bigint >> 8) & 255
  const b = bigint & 255
  return [r, g, b]
}

function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  })
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs
}

function getContrastRatio(hex1: string, hex2: string): number {
  const [r1, g1, b1] = hexToRgb(hex1)
  const [r2, g2, b2] = hexToRgb(hex2)
  const l1 = getLuminance(r1, g1, b1)
  const l2 = getLuminance(r2, g2, b2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

import { colors, aiStateTokens } from '@/design-system/tokens/colors'

describe('Design System Tokens WCAG 2.2 AA Contrast Tests', () => {
  // Operational Green Tokens from design system
  const ink900 = colors.ink[900]
  const ink50 = colors.ink[50]
  const green700 = colors.green[700]
  const green500 = colors.green[500]
  const amber700 = colors.amber[700]
  const violet700 = colors.violet[700]
  const red700 = colors.red[700]

  it('verifies dark text (Ink 900) on light surface (Ink 50) exceeds 10:1 contrast', () => {
    const ratio = getContrastRatio(ink900, ink50)
    expect(ratio).toBeGreaterThanOrEqual(10.0) // AAA compliant
  })

  it('verifies verified green text (Green 700) on light surface (Ink 50) exceeds 4.5:1 (WCAG AA)', () => {
    const ratio = getContrastRatio(green700, ink50)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })

  it('verifies warning amber text (Amber 700) on light surface (Ink 50) exceeds 4.5:1 (WCAG AA)', () => {
    const ratio = getContrastRatio(amber700, ink50)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })

  it('verifies extracted violet text (Violet 700) on light surface (Ink 50) exceeds 4.5:1 (WCAG AA)', () => {
    const ratio = getContrastRatio(violet700, ink50)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })

  it('verifies danger red text (Red 700) on light surface (Ink 50) exceeds 4.5:1 (WCAG AA)', () => {
    const ratio = getContrastRatio(red700, ink50)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })

  it('verifies white text on primary button (Green 500) exceeds 4.0:1 UI contrast', () => {
    const ratio = getContrastRatio('#FFFFFF', green500)
    expect(ratio).toBeGreaterThanOrEqual(4.0)
  })

  it('verifies all 7 canonical AI state border tokens exceed 3.0:1 on canvas (Ink 50)', () => {
    Object.entries(aiStateTokens).forEach(([name, token]) => {
      const ratio = getContrastRatio(token.border, ink50)
      expect(ratio, `ai-state-${name} border (${token.border}) failed 3.0:1 on canvas`).toBeGreaterThanOrEqual(3.0)
    })
  })
})
