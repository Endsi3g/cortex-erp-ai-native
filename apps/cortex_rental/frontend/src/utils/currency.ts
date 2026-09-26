import { formatCurrencyCAD } from '@/i18n/formatters'
import type { SupportedLocale } from '@/i18n/types'

export function formatCurrency(amount: number, locale: SupportedLocale = 'fr-CA'): string {
  return formatCurrencyCAD(amount, locale)
}
