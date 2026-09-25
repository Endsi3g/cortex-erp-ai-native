import { describe, it, expect } from 'vitest'
import { formatCurrencyCAD, formatLocalizedDate } from '@/i18n/formatters'

describe('Formatters Unit Tests (fr-CA & en-CA)', () => {
  describe('CAD Currency Formatter', () => {
    it('formats currency correctly in fr-CA (1 920,00 $)', () => {
      const result = formatCurrencyCAD(1920, 'fr-CA')
      // Note: non-breaking space \u00A0
      expect(result).toBe('1\u00A0920,00\u00A0$')
    })

    it('formats large numbers and decimals in fr-CA', () => {
      const result = formatCurrencyCAD(1250350.5, 'fr-CA')
      expect(result).toBe('1\u00A0250\u00A0350,50\u00A0$')
    })

    it('formats currency correctly in en-CA ($1,920.00)', () => {
      const result = formatCurrencyCAD(1920, 'en-CA')
      expect(result).toBe('$1,920.00')
    })

    it('formats zero and negative values gracefully', () => {
      expect(formatCurrencyCAD(0, 'fr-CA')).toBe('0,00\u00A0$')
      expect(formatCurrencyCAD(0, 'en-CA')).toBe('$0.00')
      expect(formatCurrencyCAD(NaN, 'fr-CA')).toBe('0,00\u00A0$')
    })
  })

  describe('Localized Date Formatter', () => {
    it('formats datetime in fr-CA with short french month name', () => {
      const date = new Date(2026, 8, 8, 9, 0) // Sep 8, 2026, 09:00
      const formatted = formatLocalizedDate(date, 'fr-CA', true)
      expect(formatted).toBe('8 sept. 2026, 09:00')
    })

    it('formats datetime in en-CA with AM/PM', () => {
      const date = new Date(2026, 8, 8, 9, 0) // Sep 8, 2026, 9:00 AM
      const formatted = formatLocalizedDate(date, 'en-CA', true)
      expect(formatted).toBe('Sep 8, 2026, 9:00 AM')
    })

    it('handles date only without time', () => {
      const date = new Date(2026, 8, 8)
      expect(formatLocalizedDate(date, 'fr-CA', false)).toBe('8 sept. 2026')
      expect(formatLocalizedDate(date, 'en-CA', false)).toBe('Sep 8, 2026')
    })
  })
})
