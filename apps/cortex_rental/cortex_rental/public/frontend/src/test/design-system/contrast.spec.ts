import { describe, it, expect } from 'vitest';
import {
  colors,
  aiStateTokens,
  operationalStateTokens,
} from '../../design-system/tokens/colors';

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '');
  const num = parseInt(clean, 16);
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return [r / 255, g / 255, b / 255];
}

function channelLuminance(c: number): number {
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function relativeLuminance(rgb: [number, number, number]): number {
  const [r, g, b] = rgb.map(channelLuminance);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(hexA: string, hexB: string): number {
  const l1 = relativeLuminance(hexToRgb(hexA));
  const l2 = relativeLuminance(hexToRgb(hexB));
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe('WCAG 2.2 AA Contrast Compliance Verification', () => {
  const TEXT_MIN_RATIO = 4.5;
  const GRAPHICAL_MIN_RATIO = 3.0;

  describe('Operational Business States (16 Tokens)', () => {
    Object.entries(operationalStateTokens).forEach(([key, token]) => {
      it(`passes WCAG 2.2 AA text contrast for state-${key}`, () => {
        const ratio = contrastRatio(token.bg, token.text);
        expect(ratio).toBeGreaterThanOrEqual(TEXT_MIN_RATIO);
      });

      it(`passes WCAG 2.2 graphical boundary contrast on white (#FFFFFF) for state-${key}`, () => {
        const ratio = contrastRatio('#FFFFFF', token.border);
        expect(ratio).toBeGreaterThanOrEqual(GRAPHICAL_MIN_RATIO);
      });

      it(`passes WCAG 2.2 graphical boundary contrast on canvas (#F2F7F4) for state-${key}`, () => {
        const ratio = contrastRatio('#F2F7F4', token.border);
        expect(ratio).toBeGreaterThanOrEqual(GRAPHICAL_MIN_RATIO);
      });
    });
  });

  describe('7 Canonical AI States Tokens', () => {
    Object.entries(aiStateTokens).forEach(([key, token]) => {
      it(`passes WCAG 2.2 AA text contrast for ai-state-${key}`, () => {
        const ratio = contrastRatio(token.fill, token.text);
        expect(ratio).toBeGreaterThanOrEqual(TEXT_MIN_RATIO);
      });

      it(`passes WCAG 2.2 graphical boundary contrast on canvas (#F2F7F4) for ai-state-${key}`, () => {
        const ratio = contrastRatio('#F2F7F4', token.border);
        expect(ratio).toBeGreaterThanOrEqual(GRAPHICAL_MIN_RATIO);
      });
    });
  });

  describe('Core Surface & Text Pairs', () => {
    it('primary text (#08120D) on canvas (#F2F7F4) has AAA contrast', () => {
      const ratio = contrastRatio(colors.ink[900], colors.ink[50]);
      expect(ratio).toBeGreaterThanOrEqual(7.0);
    });

    it('primary text (#08120D) on surface (#FFFFFF) has AAA contrast', () => {
      const ratio = contrastRatio(colors.ink[900], colors.surface);
      expect(ratio).toBeGreaterThanOrEqual(7.0);
    });

    it('secondary text (#264034) on surface (#FFFFFF) has AAA contrast', () => {
      const ratio = contrastRatio(colors.ink[600], colors.surface);
      expect(ratio).toBeGreaterThanOrEqual(7.0);
    });

    it('muted text (#436354) on surface (#FFFFFF) meets AA minimum (>= 4.5:1)', () => {
      const ratio = contrastRatio(colors.ink[500], colors.surface);
      expect(ratio).toBeGreaterThanOrEqual(TEXT_MIN_RATIO);
    });

    it('primary button text (#FFFFFF) on green (#087A43) meets AA minimum (>= 4.5:1)', () => {
      const ratio = contrastRatio(colors.surface, colors.green[600]);
      expect(ratio).toBeGreaterThanOrEqual(TEXT_MIN_RATIO);
    });

    it('destructive button text (#B91C1C) on danger fill (#FEF2F2) meets AA minimum (>= 4.5:1)', () => {
      const ratio = contrastRatio(colors.red[700], colors.red[50]);
      expect(ratio).toBeGreaterThanOrEqual(TEXT_MIN_RATIO);
    });
  });
});
