import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const PricingRuleSchema = z.object({
  name: z.string(),
  rule_name: z.string(),
  calendar_days: z.number(),
  billable_days: z.number(),
  is_active: z.boolean(),
  description: z.string()
})
export type PricingRule = z.infer<typeof PricingRuleSchema>

export const PricingStateSchema = ProvenanceMetaSchema.extend({
  company: z.string(),
  rules: z.array(PricingRuleSchema),
  /** Built-in curve computed by the server's pricing service, used when no active rule matches exactly. */
  reference_curve: z.array(z.object({ calendar_days: z.number(), billable_days: z.number() })),
  can_edit: z.boolean()
})
export type PricingState = z.infer<typeof PricingStateSchema>

export interface PricingRuleInput {
  name?: string
  rule_name: string
  calendar_days: number
  billable_days: number
  description?: string
  is_active: boolean
}

export const TeamMemberSchema = z.object({
  email: z.string(),
  full_name: z.string(),
  enabled: z.boolean(),
  signed_in: z.boolean(),
  last_login: z.string().nullable(),
  is_owner: z.boolean(),
  is_you: z.boolean(),
  /** Preset key held in full, or null for the owner and for a custom mix of roles. */
  preset: z.string().nullable()
})
export type TeamMember = z.infer<typeof TeamMemberSchema>

export const TeamStateSchema = ProvenanceMetaSchema.extend({
  company: z.string(),
  members: z.array(TeamMemberSchema),
  presets: z.array(z.object({ key: z.string(), label: z.string(), description: z.string() })),
  can_manage: z.boolean()
})
export type TeamState = z.infer<typeof TeamStateSchema>

export const ImportsStateSchema = ProvenanceMetaSchema.extend({
  company: z.string(),
  targets: z.array(z.object({ doctype: z.string(), label: z.string(), description: z.string(), url: z.string() })),
  history: z.array(z.object({ name: z.string(), doctype: z.string(), import_type: z.string().nullable().optional(), status: z.string().nullable().optional(), created: z.string(), by: z.string(), url: z.string() }))
})
export type ImportsState = z.infer<typeof ImportsStateSchema>

/** Rule failures come back as `ok: false` with a stable code and a message safe to show as is. */
export interface AdminWriteResult<T> {
  ok: boolean
  code?: string
  message?: string
  state?: T
}
