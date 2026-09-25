import { describe, expect, it } from 'vitest'
import { shouldUseMockApi } from '@/api'

describe('API runtime selection', () => {
  it('uses Frappe APIs in a same-origin Frappe development session', () => {
    expect(shouldUseMockApi({ mode: 'development', frappeAvailable: true })).toBe(false)
  })

  it('uses Frappe APIs in production without requiring a Vite backend URL', () => {
    expect(shouldUseMockApi({ mode: 'production', frappeAvailable: true })).toBe(false)
  })

  it('uses real endpoints in standalone development and allows an explicit mock override', () => {
    expect(shouldUseMockApi({ mode: 'development', frappeAvailable: false })).toBe(false)
    expect(shouldUseMockApi({ mode: 'production', backendUrl: 'https://erp.example.test' })).toBe(false)
    expect(shouldUseMockApi({ forceMock: true, mode: 'production', frappeAvailable: true })).toBe(true)
  })
})
