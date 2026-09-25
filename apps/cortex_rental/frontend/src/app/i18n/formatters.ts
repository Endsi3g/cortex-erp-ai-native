import type { LocaleType } from './index'

/**
 * Localized CAD currency formatter.
 * fr-CA: 1 920,00 $ (non-breaking space \u00A0 before $)
 * en-CA: $1,920.00
 */
export function formatCurrencyCAD(amount: number, locale: LocaleType = 'fr-CA'): string {
  if (isNaN(amount)) return locale === 'fr-CA' ? '0,00\u00A0$' : '$0.00'

  if (locale === 'fr-CA') {
    const formatted = new Intl.NumberFormat('fr-CA', {
      style: 'currency',
      currency: 'CAD',
      currencyDisplay: 'narrowSymbol',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
    return formatted.replace(/\s/g, '\u00A0')
  } else {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
      currencyDisplay: 'narrowSymbol',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }
}

/**
 * Localized Date & Time Formatter.
 * fr-CA: 8 sept. 2026, 09:00
 * en-CA: Sep 8, 2026, 9:00 AM
 */
/**
 * Frappe sends dates as "YYYY-MM-DD" and datetimes as "YYYY-MM-DD HH:MM:SS"
 * in the site's time zone. `new Date("YYYY-MM-DD")` would read them as UTC
 * midnight and show the previous day west of Greenwich, so both forms are
 * read as local calendar values here.
 */
export function parseFrappeDate(value: string | Date): Date {
  if (value instanceof Date) return value
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(value.trim().replace(/\.\d+$/, ''))
  if (match) {
    const [, y, m, d, hh = '0', mm = '0', ss = '0'] = match
    return new Date(Number(y), Number(m) - 1, Number(d), Number(hh), Number(mm), Number(ss))
  }
  return new Date(value)
}

export function formatDateTime(dateInput: string | Date, locale: LocaleType = 'fr-CA'): string {
  const date = parseFrappeDate(dateInput)
  if (isNaN(date.getTime())) return '—'

  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: locale === 'en-CA'
  }).format(date)
}

/**
 * Localized Date-only Formatter.
 */
export function formatDate(dateInput: string | Date, locale: LocaleType = 'fr-CA'): string {
  const date = parseFrappeDate(dateInput)
  if (isNaN(date.getTime())) return '—'

  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).format(date)
}

/** Money in the document's own currency (company or presentation currency), never assumed CAD. */
export function formatMoney(amount: number | null | undefined, currency: string | null | undefined, locale: LocaleType = 'fr-CA'): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return '—'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency || 'CAD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount)
}

/** Short axis labels: 0, 250 k, 1 M (fr-CA) / 0, 250K, 1M (en-CA). */
export function formatCompactNumber(value: number, locale: LocaleType = 'fr-CA'): string {
  return new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}
