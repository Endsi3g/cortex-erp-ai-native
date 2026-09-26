import { ROUTER_BASE } from '@/app/router/routes'

/** App route → URL of the same page in embed mode (no rail, no top bar), for the artifact panel. */
export function embedUrl(route: string, pathname: string = typeof window === 'undefined' ? '' : window.location.pathname): string {
  const withEmbed = route + (route.includes('?') ? '&' : '?') + 'embed=1'
  if (pathname.startsWith('/preview')) return `/preview/?route=${encodeURIComponent(withEmbed)}`
  return ROUTER_BASE.replace(/\/$/, '') + withEmbed
}
