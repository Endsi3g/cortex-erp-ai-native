type CsrfWindow = Window & { csrf_token?: string; frappe?: { boot?: { csrf_token?: string } } }

/**
 * CSRF token of the current Frappe session. Standalone app: `window.csrf_token`, written into www/cortex.html
 * from the server boot data. Desk-hosted screens: `frappe.boot.csrf_token`. Last resort: the `csrf_token` cookie.
 */
export function getCsrfToken(): string | null {
  if (typeof window === 'undefined') return null
  const w = window as CsrfWindow
  const token = w.csrf_token || w.frappe?.boot?.csrf_token
  if (token && token !== '{{ csrf_token }}') return token
  if (typeof document === 'undefined') return null
  const cookie = document.cookie.split('; ').find((c) => c.startsWith('csrf_token='))?.split('=').slice(1).join('=')
  return cookie ? decodeURIComponent(cookie) : null
}
