import { z } from 'zod'
import { ProvenanceMetaSchema } from './common'

export const OnboardingStepSchema = z.object({
  key: z.enum(['profile', 'team', 'catalog', 'policies']),
  title: z.string(),
  done: z.boolean(),
  optional: z.boolean(),
  current: z.boolean()
})
export type OnboardingStep = z.infer<typeof OnboardingStepSchema>

export const OnboardingStateSchema = ProvenanceMetaSchema.extend({
  company: z.string(),
  status: z.enum(['In Progress', 'Completed']),
  is_owner: z.boolean(),
  steps: z.array(OnboardingStepSchema),
  progress: z.object({ done: z.number(), total: z.number() }),
  profile: z.object({
    company_name: z.string(),
    country: z.string().nullable().optional(),
    default_currency: z.string().nullable().optional(),
    tax_id: z.string(),
    phone_no: z.string(),
    website: z.string(),
    time_zone: z.string(),
    language: z.string()
  }),
  team: z.array(z.object({ email: z.string(), full_name: z.string().nullable().optional(), enabled: z.boolean(), signed_in: z.boolean() })),
  role_presets: z.array(z.object({ key: z.string(), label: z.string(), description: z.string() })),
  catalog: z.object({ equipment_count: z.number(), import_url: z.string(), equipment_url: z.string() }),
  policies: z.object({ rules: z.array(z.object({ name: z.string(), rule_name: z.string(), calendar_days: z.number(), billable_days: z.number() })) })
})
export type OnboardingState = z.infer<typeof OnboardingStateSchema>

export const OnboardingChoicesSchema = ProvenanceMetaSchema.extend({
  countries: z.array(z.string()),
  currencies: z.array(z.string()),
  languages: z.array(z.object({ name: z.string(), label: z.string() }))
})
export type OnboardingChoices = z.infer<typeof OnboardingChoicesSchema>

export interface CompanyProfileInput {
  country: string
  default_currency: string
  tax_id?: string
  phone_no?: string
  website?: string
  time_zone?: string
  language?: string
}

/** Rule failures come back as `ok: false` with a stable code and a message safe to show as is. */
export interface OnboardingWriteResult {
  ok: boolean
  code?: string
  message?: string
  state?: OnboardingState
  email?: string
  email_sent?: boolean
  setup_link?: string
}
