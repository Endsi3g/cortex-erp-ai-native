import { getCsrfToken } from '@/utils/csrf'

/** Guest-safe calls used by the sign-in screens. Plain `fetch`: errors are answered inline, never in a Frappe dialog. */

export class AuthRequestError extends Error {
  constructor(
    readonly status: number,
    message: string
  ) {
    super(message)
    this.name = 'AuthRequestError'
  }
}

export interface LoginProvider { name: string; label: string; url: string; icon: string }
export interface LoginOptions {
  providers: LoginProvider[]
  email_link: boolean
  password_login: boolean
  signup_enabled: boolean
  redirect_to: string
}

export interface AccessRequestPayload {
  full_name: string
  email: string
  company_name: string
  job_title: string
  team_size: string
  accept_terms: number
  website: string
}
export interface AccessResult { ok: boolean; code?: string; message?: string }

const EMAIL_RE = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/
const FREE_DOMAINS = ['gmail.com', 'googlemail.com', 'outlook.com', 'hotmail.com', 'live.com', 'msn.com', 'yahoo.com', 'yahoo.ca', 'yahoo.fr', 'icloud.com', 'me.com', 'aol.com', 'proton.me', 'protonmail.com', 'gmx.com', 'mail.com', 'videotron.ca', 'bell.net']

export const isEmail = (value: string) => EMAIL_RE.test(value.trim())
export const isFreeEmail = (value: string) => FREE_DOMAINS.includes(value.trim().toLowerCase().split('@')[1] ?? '')

export function failureMessage(error: unknown): string {
  if (error instanceof AuthRequestError && error.status === 429) return 'Trop de tentatives. Patientez quelques minutes avant de réessayer.'
  return 'La connexion au serveur a échoué. Vos informations sont conservées : réessayez dans un instant.'
}

async function call<T>(method: string, options: { verb?: 'GET' | 'POST'; args?: Record<string, string | number> } = {}): Promise<{ status: number; body: T | null }> {
  const verb = options.verb ?? 'POST'
  const params = new URLSearchParams(Object.entries(options.args ?? {}).map(([k, v]) => [k, String(v)]))
  const url = `/api/method/${method}${verb === 'GET' && params.size ? `?${params}` : ''}`
  const csrf = getCsrfToken()
  const response = await fetch(url, {
    method: verb,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(verb === 'POST' ? { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' } : {}),
      ...(csrf ? { 'X-Frappe-CSRF-Token': csrf } : {})
    },
    body: verb === 'POST' ? params.toString() : undefined
  }).catch(() => null)
  if (!response) throw new AuthRequestError(0, 'network')
  const body = (await response.json().catch(() => null)) as T | null
  return { status: response.status, body }
}

const unwrap = <T>(result: { status: number; body: { message?: T } | null }): T | undefined => result.body?.message

export async function fetchLoginOptions(redirectTo: string): Promise<LoginOptions | null> {
  try {
    const result = await call<{ message: LoginOptions }>('cortex_rental.api.v1.access.login_options', { verb: 'GET', args: { redirect_to: redirectTo } })
    return result.status === 200 ? (unwrap(result) ?? null) : null
  } catch {
    return null
  }
}

export type SignInOutcome = { ok: true } | { ok: false; reason: 'invalid' | 'two_factor' | 'rate_limited' | 'network' }

export async function signIn(usr: string, pwd: string): Promise<SignInOutcome> {
  try {
    const result = await call<{ message?: string; verification?: unknown; tmp_id?: string }>('login', { args: { usr, pwd } })
    if (result.status === 429) return { ok: false, reason: 'rate_limited' }
    if (result.body?.verification || result.body?.tmp_id) return { ok: false, reason: 'two_factor' }
    if (result.status === 200 && ['Logged In', 'No App'].includes(String(result.body?.message))) return { ok: true }
    return { ok: false, reason: 'invalid' }
  } catch {
    return { ok: false, reason: 'network' }
  }
}

/** Frappe answers the same way whether or not the account exists, so callers show the same confirmation. */
export async function sendResetLink(email: string): Promise<void> {
  const result = await call('frappe.core.doctype.user.user.reset_password', { args: { user: email } })
  if (result.status === 429) throw new AuthRequestError(429, 'rate')
  if (result.status >= 500) throw new AuthRequestError(result.status, 'server')
}

export async function sendLoginLink(email: string): Promise<void> {
  const result = await call('frappe.www.login.send_login_link', { args: { email } })
  if (result.status === 429) throw new AuthRequestError(429, 'rate')
  if (result.status >= 500) throw new AuthRequestError(result.status, 'server')
}

export async function requestAccess(payload: AccessRequestPayload): Promise<AccessResult> {
  const result = await call<{ message?: AccessResult }>('cortex_rental.api.v1.access.request_access', { args: { ...payload } })
  if (result.status === 429) throw new AuthRequestError(429, 'rate')
  const message = unwrap(result)
  if (result.status !== 200 || !message) throw new AuthRequestError(result.status, 'server')
  return message
}
