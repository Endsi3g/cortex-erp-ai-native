import type { RouteRecordRaw, Router } from 'vue-router'

/**
 * The standalone app is served at /cortex, so its URLs are `/cortex/rentals`, not `/cortex/app/cortex-rentals`.
 * Route definitions keep the canonical `/app/cortex-*` paths (used by the Desk host and by every link in the
 * screens); the standalone router shortens them and redirects any canonical path it is handed.
 */
export const STANDALONE_BASE = '/cortex'
const CANONICAL_PREFIX = '/app/cortex-'

export const toStandalonePath = (path: string): string =>
  path.startsWith(CANONICAL_PREFIX) ? `/${path.slice(CANONICAL_PREFIX.length)}` : path

export function standaloneRoutes(routes: RouteRecordRaw[]): RouteRecordRaw[] {
  return routes.map((route) => {
    const path = toStandalonePath(route.path)
    if (route.redirect === '/app/cortex-operations') return { ...route, path, redirect: '/operations' } as RouteRecordRaw
    return { ...route, path } as RouteRecordRaw
  })
}

/** Rewrites canonical `/app/cortex-*` targets (router-link, router.push, redirects) to the standalone URL. */
export function setupStandalonePaths(router: Router): void {
  router.beforeEach((to) => {
    if (!to.path.startsWith(CANONICAL_PREFIX)) return true
    return { path: toStandalonePath(to.path), query: to.query, hash: to.hash, replace: true }
  })
}
