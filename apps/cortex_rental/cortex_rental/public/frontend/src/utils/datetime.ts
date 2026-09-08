import { formatLocalizedDate } from '@/i18n/formatters'
import type { SupportedLocale } from '@/i18n/types'

export function formatDate(date: string | Date, locale: SupportedLocale = 'fr-CA', includeTime = true): string {
  return formatLocalizedDate(date, locale, includeTime)
}
