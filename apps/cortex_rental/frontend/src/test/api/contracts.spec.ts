import { describe, it, expect } from 'vitest'
import {
  MutationResponseSchema,
  RentalTransactionSchema,
  OwnerStatementSafeSchema,
  ApprovalRequestItemSchema
} from '@/api/contracts'
import { initialRentals } from '@/api/mock/fixtures/rentals'
import { initialOwnerStatements } from '@/api/mock/fixtures/consignment'
import { initialApprovals } from '@/api/mock/fixtures/approvals'

describe('API Contracts & Zod Schemas Validation Tests', () => {
  it('validates MutationResponseSchema with valid and invalid statuses', () => {
    const valid = {
      request_id: 'req-123',
      status: 'completed',
      approval_required: false,
      mutation_performed: true
    }
    expect(MutationResponseSchema.safeParse(valid).success).toBe(true)

    const invalidStatus = {
      request_id: 'req-123',
      status: 'invalid_status',
      approval_required: false,
      mutation_performed: true
    }
    expect(MutationResponseSchema.safeParse(invalidStatus).success).toBe(false)
  })

  it('validates RentalTransactionSchema against initial rental fixtures', () => {
    initialRentals.forEach((rental) => {
      const parseResult = RentalTransactionSchema.safeParse(rental)
      expect(parseResult.success, JSON.stringify(parseResult)).toBe(true)
    })
  })

  it('validates OwnerStatementSafeSchema against initial statement fixtures', () => {
    Object.values(initialOwnerStatements).forEach((statement) => {
      const parseResult = OwnerStatementSafeSchema.safeParse(statement)
      expect(parseResult.success, JSON.stringify(parseResult)).toBe(true)
    })
  })

  it('validates ApprovalRequestItemSchema against approval fixtures', () => {
    initialApprovals.forEach((item) => {
      const parseResult = ApprovalRequestItemSchema.safeParse(item)
      expect(parseResult.success, JSON.stringify(parseResult)).toBe(true)
    })
  })
})
