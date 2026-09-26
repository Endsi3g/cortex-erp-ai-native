import { expect } from 'vitest'
import { containsRenterPii } from '@/utils/privacy'

export function assertNoRenterPii(data: unknown) {
  const result = containsRenterPii(data)
  expect(result.hasPii).toBe(false)
  expect(result.violations).toHaveLength(0)
}
