import { STANDALONE_BASE } from '@/app/router/standalone'

/** A redirect coming from the query string is honoured only when it is a path inside the app. */
export function redirectTarget(raw: unknown): string {
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return '/operations'
  if (value.startsWith('/login') || value.startsWith('/forgot-password') || value.startsWith('/request-access')) return '/operations'
  return value
}

/** Absolute URL of an in-app path, e.g. `/rentals` -> `/cortex/rentals` (the router base is not in `router.push` paths). */
export const landingUrl = (path: string): string => `${STANDALONE_BASE}${path.startsWith('/app/cortex-') ? `/${path.slice('/app/cortex-'.length)}` : path}`
