import type { SupportedLocale } from './types'

export function formatCurrencyCAD(amount: number, locale: SupportedLocale = 'fr-CA'): string {
  if (isNaN(amount)) return locale === 'fr-CA' ? '0,00\u00A0$' : '$0.00'

  const isNegative = amount < 0
  const absAmount = Math.abs(amount)
  const parts = absAmount.toFixed(2).split('.')
  const integerPart = parts[0] || '0'
  const decimalPart = parts[1] || '00'

  if (locale === 'fr-CA') {
    // Canadian French convention: 1 920,00 $ (negative: -1 920,00 $)
    const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0') // non-breaking space
    const sign = isNegative ? '-' : ''
    return `${sign}${formattedInteger},${decimalPart}\u00A0$`
  } else {
    // Canadian English convention: $1,920.00 (negative: -$1,920.00)
    const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    const sign = isNegative ? '-' : ''
    return `${sign}$${formattedInteger}.${decimalPart}`
  }
}

export function formatLocalizedDate(dateInput: string | Date, locale: SupportedLocale = 'fr-CA', includeTime = true): string {
  const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
  if (isNaN(d.getTime())) return ''

  if (locale === 'fr-CA') {
    const months = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
    const day = d.getDate()
    const month = months[d.getMonth()]
    const year = d.getFullYear()
    if (!includeTime) return `${day} ${month} ${year}`
    const hours = String(d.getHours()).padStart(2, '0')
    const minutes = String(d.getMinutes()).padStart(2, '0')
    return `${day} ${month} ${year}, ${hours}:${minutes}`
  } else {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const day = d.getDate()
    const month = months[d.getMonth()]
    const year = d.getFullYear()
    if (!includeTime) return `${month} ${day}, ${year}`
    let hours = d.getHours()
    const ampm = hours >= 12 ? 'PM' : 'AM'
    hours = hours % 12 || 12
    const minutes = String(d.getMinutes()).padStart(2, '0')
    return `${month} ${day}, ${year}, ${hours}:${minutes} ${ampm}`
  }
}
