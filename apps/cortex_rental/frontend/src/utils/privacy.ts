import { FORBIDDEN_RENTER_PII_KEYS, type PrivacySanitizeResult } from '@/types/privacy'
import type { OwnerStatementSafe, OwnerStatementLineSafe } from '@/types/consignment'
import { OwnerStatementSafeSchema } from '@/api/contracts/consignment'

/**
 * Checks whether an arbitrary object, array, or string contains any forbidden renter PII keys or substrings.
 */
export function containsRenterPii(data: unknown): { hasPii: boolean; violations: string[] } {
  const violations: string[] = []

  function inspect(val: unknown, path = '') {
    if (!val || typeof val !== 'object') return

    if (Array.isArray(val)) {
      val.forEach((item, index) => inspect(item, `${path}[${index}]`))
      return
    }

    const obj = val as Record<string, unknown>
    for (const key of Object.keys(obj)) {
      const currentPath = path ? `${path}.${key}` : key
      const lowerKey = key.toLowerCase()

      for (const forbidden of FORBIDDEN_RENTER_PII_KEYS) {
        if (lowerKey === forbidden || lowerKey.includes(forbidden)) {
          violations.push(`Forbidden PII key detected at '${currentPath}' (matched '${forbidden}')`)
        }
      }

      inspect(obj[key], currentPath)
    }
  }

  inspect(data)
  return {
    hasPii: violations.length > 0,
    violations
  }
}

/**
 * Sanitizes arbitrary consignment data into a strictly validated, pure OwnerStatementSafe record.
 * Strips all forbidden renter PII keys recursively and validates the final payload with Zod.
 */
export function sanitizeOwnerStatement(input: unknown): PrivacySanitizeResult<OwnerStatementSafe> {
  const removedKeys: string[] = []

  function strip(val: unknown, path = ''): unknown {
    if (!val || typeof val !== 'object') return val

    if (Array.isArray(val)) {
      return val.map((item, idx) => strip(item, `${path}[${idx}]`))
    }

    const obj = val as Record<string, unknown>
    const cleanObj: Record<string, unknown> = {}

    for (const [key, value] of Object.entries(obj)) {
      const currentPath = path ? `${path}.${key}` : key
      const lowerKey = key.toLowerCase()

      let isForbidden = false
      for (const forbidden of FORBIDDEN_RENTER_PII_KEYS) {
        if (lowerKey === forbidden || lowerKey.includes(forbidden)) {
          isForbidden = true
          removedKeys.push(currentPath)
          break
        }
      }

      if (!isForbidden) {
        cleanObj[key] = strip(value, currentPath)
      }
    }

    return cleanObj
  }

  const cleanRaw = strip(input) as Record<string, unknown>

  // Construct pure OwnerStatementSafe
  const ownerObj = (cleanRaw.owner || {}) as Record<string, unknown>
  const periodObj = (cleanRaw.period || {}) as Record<string, unknown>
  const totalsObj = (cleanRaw.totals || {}) as Record<string, unknown>
  const rawLines = Array.isArray(cleanRaw.lines) ? cleanRaw.lines : []

  const cleanLines: OwnerStatementLineSafe[] = rawLines.map((line) => {
    const l = (line || {}) as Record<string, unknown>
    return {
      serial_number: String(l.serial_number || ''),
      equipment_name: String(l.equipment_name || ''),
      rental_start_date: String(l.rental_start_date || ''),
      rental_end_date: String(l.rental_end_date || ''),
      billable_days: Number(l.billable_days || 0),
      rate: Number(l.rate || 0),
      discount_amount: Number(l.discount_amount || 0),
      consignment_percentage: Number(l.consignment_percentage || 0),
      owner_amount: Number(l.owner_amount || 0),
      invoice_reference: String(l.invoice_reference || '')
    }
  })

  const safeRecord: OwnerStatementSafe = {
    owner: {
      id: String(ownerObj.id || ''),
      display_name: String(ownerObj.display_name || ''),
      code: String(ownerObj.code || '')
    },
    period: {
      start: String(periodObj.start || ''),
      end: String(periodObj.end || ''),
      timezone: String(periodObj.timezone || 'America/Toronto')
    },
    currency: 'CAD',
    totals: {
      eligible_net_revenue: Number(totalsObj.eligible_net_revenue || 0),
      owner_amount_due: Number(totalsObj.owner_amount_due || 0)
    },
    lines: cleanLines,
    generated_at: String(cleanRaw.generated_at || new Date().toISOString()),
    snapshot_version: String(cleanRaw.snapshot_version || 'v1.0')
  }

  // Runtime schema validation
  OwnerStatementSafeSchema.parse(safeRecord)

  return {
    sanitized: safeRecord,
    removedKeys,
    isClean: removedKeys.length === 0
  }
}

/**
 * Asserts that an object conforms to OwnerStatementSafe and contains zero forbidden PII.
 */
export function assertOwnerStatementSafe(data: unknown): asserts data is OwnerStatementSafe {
  const piiCheck = containsRenterPii(data)
  if (piiCheck.hasPii) {
    throw new Error(`Privacy assertion failed: ${piiCheck.violations.join('; ')}`)
  }
  OwnerStatementSafeSchema.parse(data)
}
