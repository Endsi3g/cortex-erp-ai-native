import { describe, it, expect } from 'vitest'
import { sanitizeBarcodeInput, detectBarcodeType } from '@/utils/scanner'

describe('Scanner Utility Unit Tests', () => {
  it('sanitizes barcode input by trimming whitespace and control characters', () => {
    expect(sanitizeBarcodeInput('  DEMO-SN-ALX-001\r\n\t ')).toBe('DEMO-SN-ALX-001')
    expect(sanitizeBarcodeInput('')).toBe('')
  })

  it('detects barcode entity types correctly', () => {
    expect(detectBarcodeType('DEMO-SN-ALX-001')).toBe('serial')
    expect(detectBarcodeType('SN-12345')).toBe('serial')
    expect(detectBarcodeType('DEMO-ITM-ALX35')).toBe('item')
    expect(detectBarcodeType('ITM-CKE')).toBe('item')
    expect(detectBarcodeType('DEMO-TRX-2026-001')).toBe('rental')
    expect(detectBarcodeType('TRX-9988')).toBe('rental')
    expect(detectBarcodeType('UNKNOWN_CODE_XYZ')).toBe('unknown')
  })
})
