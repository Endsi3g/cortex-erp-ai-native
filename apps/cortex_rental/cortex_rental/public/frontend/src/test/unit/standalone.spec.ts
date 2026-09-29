import { describe, it, expect, afterEach } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '@/app/router/routes'
import { setupStandalonePaths, standaloneRoutes, toStandalonePath } from '@/app/router/standalone'
import { landingUrl, redirectTarget } from '@/features/auth/landing'
import { isEmail, isFreeEmail } from '@/features/auth/authApi'
import { getCsrfToken } from '@/utils/csrf'

describe('standalone app URLs (/cortex)', () => {
  it('shortens canonical Desk paths', () => {
    expect(toStandalonePath('/app/cortex-rentals')).toBe('/rentals')
    expect(toStandalonePath('/app/cortex-rental/:id')).toBe('/rental/:id')
    expect(toStandalonePath('/login')).toBe('/login')
  })

  it('keeps route names and metadata, only the paths change', () => {
    const shortened = standaloneRoutes(routes)
    expect(shortened.map((r) => r.name)).toEqual(routes.map((r) => r.name))
    expect(shortened.find((r) => r.name === 'rentals-list')?.path).toBe('/rentals')
    expect(shortened.find((r) => r.path === '/')?.redirect).toBe('/operations')
    expect(shortened.some((r) => r.path.startsWith('/app/cortex-'))).toBe(false)
  })

  it('rewrites a canonical link handed to the router, query and hash included', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: standaloneRoutes(routes) })
    setupStandalonePaths(router)
    await router.push('/app/cortex-rentals?state=Contract#top')
    expect(router.currentRoute.value.path).toBe('/rentals')
    expect(router.currentRoute.value.query.state).toBe('Contract')
  })
})

describe('sign-in helpers', () => {
  it('only honours redirects inside the app', () => {
    expect(redirectTarget('/rentals')).toBe('/rentals')
    for (const bad of ['//evil.test', 'https://evil.test', '/\\evil', undefined, 42, '/login']) expect(redirectTarget(bad)).toBe('/operations')
  })

  it('builds absolute app URLs', () => {
    expect(landingUrl('/rentals')).toBe('/cortex/rentals')
    expect(landingUrl('/app/cortex-rental/CR-1')).toBe('/cortex/rental/CR-1')
  })

  it('validates work emails like the server does', () => {
    expect(isEmail(' camille@entreprise.com ')).toBe(true)
    expect(isEmail('camille@')).toBe(false)
    expect(isFreeEmail('camille@Gmail.com')).toBe(true)
    expect(isFreeEmail('camille@entreprise.com')).toBe(false)
  })
})

describe('CSRF token', () => {
  const w = window as Window & { csrf_token?: string }
  afterEach(() => {
    delete w.csrf_token
  })

  it('reads the boot token written into www/cortex.html and ignores an unrendered template placeholder', () => {
    w.csrf_token = 'abc123'
    expect(getCsrfToken()).toBe('abc123')
    w.csrf_token = '{{ csrf_token }}'
    expect(getCsrfToken()).toBeNull()
  })
})
