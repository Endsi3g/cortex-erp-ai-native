/**
 * CSV export helpers shared by report screens.
 *
 * Text cells that a spreadsheet would evaluate as a formula (leading =, +,
 * -, @, tab or carriage return) are prefixed with a single quote, so an
 * account or customer name can never execute when the file is opened.
 * Numbers are written raw.
 */
const FORMULA_PREFIX = /^[=+\-@\t\r]/

export function csvCell(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : ''
  const text = FORMULA_PREFIX.test(value) ? `'${value}` : value
  return /[",\n\r;]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function toCsv(rows: Array<Array<string | number | null | undefined>>): string {
  return rows.map(row => row.map(csvCell).join(',')).join('\r\n')
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob(['﻿', csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename.replace(/[^\w.\-]+/g, '-')
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
