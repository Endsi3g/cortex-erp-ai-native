import { describe, it, expect } from 'vitest';
import {
  colors,
  aiStateTokens,
  operationalStateTokens,
  type AiStateType,
  type OperationalStateType,
} from '../../design-system/tokens/colors';
import { typography, formatCurrencyCad } from '../../design-system/tokens/typography';
import { spacing } from '../../design-system/tokens/spacing';
import { radius } from '../../design-system/tokens/radius';
import { elevation } from '../../design-system/tokens/elevation';
import { motion } from '../../design-system/tokens/motion';

describe('Design System Tokens — Cortex OS Operational Green', () => {
  describe('Brand Colors & Palette Structure', () => {
    it('defines primary Operational Green core tokens', () => {
      expect(colors.green[500]).toBe('#087A43');
      expect(colors.green[600]).toBe('#087A43');
      expect(colors.green[50]).toBe('#EDFBF2');
      expect(colors.green[800]).toBe('#044727');
    });

    it('defines Ink neutrals with canvas #F2F7F4 and surface #FFFFFF', () => {
      expect(colors.ink[50]).toBe('#F2F7F4');
      expect(colors.ink[900]).toBe('#08120D');
      expect(colors.surface).toBe('#FFFFFF');
    });
  });

  describe('7 Canonical AI States Triple-Encoding', () => {
    const canonicalStates: AiStateType[] = [
      'verified',
      'extracted',
      'proposed',
      'needs_confirmation',
      'approval_required',
      'approved_executed',
      'blocked_by_policy',
    ];

    it('defines all 7 canonical states with required attributes', () => {
      expect(Object.keys(aiStateTokens)).toHaveLength(7);
      for (const state of canonicalStates) {
        const config = aiStateTokens[state];
        expect(config).toBeDefined();
        expect(config.fill).toMatch(/^#[0-9A-Fa-f]{6}$/);
        expect(config.text).toMatch(/^#[0-9A-Fa-f]{6}$/);
        expect(config.border).toMatch(/^#[0-9A-Fa-f]{6}$/);
        expect(config.icon).toBeTruthy();
        expect(config.labelFr).toBeTruthy();
        expect(config.labelEn).toBeTruthy();
      }
    });

    it('enforces dashed border exclusively for proposed state', () => {
      expect(aiStateTokens.proposed.borderStyle).toBe('dashed');
      expect(aiStateTokens.verified.borderStyle).toBe('solid');
      expect(aiStateTokens.approved_executed.borderStyle).toBe('solid');
    });

    it('maps accurate localized labels for all AI states', () => {
      expect(aiStateTokens.verified.labelFr).toBe('Vérifié dans Cortex');
      expect(aiStateTokens.verified.labelEn).toBe('Verified in Cortex');
      expect(aiStateTokens.extracted.labelFr).toBe('Extrait de la source');
      expect(aiStateTokens.extracted.labelEn).toBe('Extracted from source');
      expect(aiStateTokens.proposed.labelFr).toBe('Proposé — non exécuté');
      expect(aiStateTokens.proposed.labelEn).toBe('Proposed — not executed');
      expect(aiStateTokens.needs_confirmation.labelFr).toBe('À confirmer');
      expect(aiStateTokens.needs_confirmation.labelEn).toBe('Needs confirmation');
      expect(aiStateTokens.approval_required.labelFr).toBe('Approbation requise');
      expect(aiStateTokens.approval_required.labelEn).toBe('Approval required');
      expect(aiStateTokens.approved_executed.labelFr).toBe('Approuvé et exécuté');
      expect(aiStateTokens.approved_executed.labelEn).toBe('Approved and executed');
      expect(aiStateTokens.blocked_by_policy.labelFr).toBe('Bloqué par policy');
      expect(aiStateTokens.blocked_by_policy.labelEn).toBe('Blocked by policy');
    });
  });

  describe('Operational Business States Tokens', () => {
    const expectedStates: OperationalStateType[] = [
      'quote',
      'draft',
      'reservation',
      'contract',
      'checked_out',
      'partial_return',
      'returned',
      'invoice_prepared',
      'invoiced',
      'closed',
      'cancelled',
      'disputed',
      'conflict',
      'quarantine',
      'repair',
      'missing',
    ];

    it('defines all 16 operational business state tokens', () => {
      expect(Object.keys(operationalStateTokens)).toHaveLength(16);
      for (const state of expectedStates) {
        const config = operationalStateTokens[state];
        expect(config).toBeDefined();
        expect(config.bg).toMatch(/^#[0-9A-Fa-f]{6}$/);
        expect(config.text).toMatch(/^#[0-9A-Fa-f]{6}$/);
        expect(config.border).toMatch(/^#[0-9A-Fa-f]{6}$/);
        expect(config.labelFr).toBeTruthy();
        expect(config.labelEn).toBeTruthy();
        expect(config.icon).toBeTruthy();
      }
    });
  });

  describe('Typography & CAD Currency Formatting', () => {
    it('enforces Inter for sans and JetBrains Mono for mono', () => {
      expect(typography.fontFamily.sans).toContain('Inter');
      expect(typography.fontFamily.mono).toContain('JetBrains Mono');
    });

    it('formats CAD currency according to Canadian French standards (1 920,00 $)', () => {
      const formattedFr = formatCurrencyCad(1920, 'fr-CA');
      // Normalize non-breaking spaces for universal comparison
      const normalizedFr = formattedFr.replace(/\u00A0|\u202F/g, ' ');
      expect(normalizedFr).toContain('1 920,00');
      expect(normalizedFr).toContain('$');
    });

    it('formats CAD currency according to Canadian English standards ($1,920.00)', () => {
      const formattedEn = formatCurrencyCad(1920, 'en-CA');
      expect(formattedEn).toContain('$1,920.00');
    });
  });

  describe('Spatial, Radius, Elevation & Motion Systems', () => {
    it('follows 4px base spacing scale', () => {
      expect(spacing[1]).toBe('4px');
      expect(spacing[2]).toBe('8px');
      expect(spacing[3]).toBe('12px');
      expect(spacing[4]).toBe('16px');
      expect(spacing[16]).toBe('64px');
    });

    it('defines standard border radii including 6px, 8px, 12px, pill', () => {
      expect(radius.sm).toBe('6px');
      expect(radius.md).toBe('8px');
      expect(radius.lg).toBe('12px');
      expect(radius.pill).toBe('9999px');
    });

    it('defines subtle elevation shadows', () => {
      expect(elevation.xs).toContain('rgba');
      expect(elevation.drawer).toContain('-8px');
    });

    it('defines motion tokens with reduced-motion override', () => {
      expect(motion.duration.fast).toBe('120ms');
      expect(motion.duration.base).toBe('180ms');
      expect(motion.duration.slow).toBe('240ms');
      expect(motion.transition.reduced).toContain('0.001ms');
    });
  });
});
