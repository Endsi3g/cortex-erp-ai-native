export const FORBIDDEN_RENTER_PII_KEYS = [
  'customer_name',
  'customer_email',
  'customer_phone',
  'customer_address',
  'customer_id',
  'customer_payment_information',
  'customer_language',
  'customer_contact',
  'customer_document',
  'customer_file_url',
  'customer_billing_address',
  'customer_shipping_address',
  'client_name',
  'client_email',
  'client_phone',
  'client_address',
  'billing_address',
  'shipping_address',
  'renter_id',
  'renter_name',
  'renter_email',
  'renter_phone',
  'renter_address',
  'project_name',
  'project_notes',
  'communication_body'
] as const

export type ForbiddenRenterPiiKey = typeof FORBIDDEN_RENTER_PII_KEYS[number]

export interface PrivacySanitizeResult<T> {
  sanitized: T
  removedKeys: string[]
  isClean: boolean
}
