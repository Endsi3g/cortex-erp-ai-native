import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { createAppRouter } from '@/app/router'
import { routes } from '@/app/router/routes'
import { useSessionStore } from '@/stores/session'
import { useCopilotStore } from '@/stores/copilot'

describe('Cortex OS — Router & Navigation Architecture (canonical routes)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const session = useSessionStore()
    session.currentUser = { id: 'test-user', email: 'test@example.test', full_name: 'Test User', roles: ['System Manager'], permissions: [] }
    session.isAuthenticated = true
    session.userCompanies = [{ id: 'Test Company', name: 'Test Company', code: 'Test Company' }]
    session.activeCompanyId = 'Test Company'
  })
  afterEach(() => vi.unstubAllGlobals())

  it('R-TEST-1: Defines all 24 canonical routes with complete CortexRouteMeta', () => {
    expect(routes.length).toBeGreaterThanOrEqual(24)

    const canonicalScreenIds = Array.from({ length: 24 }, (_, i) => i + 1)
    
    // Check that every canonical screen ID 1 through 24 is covered
    for (const id of canonicalScreenIds) {
      const matchingRoute = routes.find(r => r.meta?.screenId === id)
      expect(matchingRoute, `Route for canonical Screen #${id} must exist`).toBeDefined()
      expect(matchingRoute?.meta?.titleKey).toBeDefined()
      expect(matchingRoute?.meta?.priority).toMatch(/^P[012]$/)
      expect(matchingRoute?.meta?.layout).toBeDefined()
    }
  })

  it('R-TEST-2: Root path redirects directly to Operations Overview (/app/cortex-operations)', async () => {
    const router = createAppRouter(true)
    await router.push('/')
    expect(router.currentRoute.value.path).toBe('/app/cortex-operations')
    expect(router.currentRoute.value.name).toBe('operations-overview')
  })

  it('R-TEST-3: Navigates across P0 demo-critical routes successfully', async () => {
    const router = createAppRouter(true)

    // 1. Operations Overview
    await router.push('/app/cortex-operations')
    expect(router.currentRoute.value.name).toBe('operations-overview')
    expect(router.currentRoute.value.meta.priority).toBe('P0')

    // 2. Availability Matrix
    await router.push('/app/cortex-availability')
    expect(router.currentRoute.value.name).toBe('availability-matrix')
    expect(router.currentRoute.value.meta.priority).toBe('P0')

    // 3. Rentals List
    await router.push('/app/cortex-rentals')
    expect(router.currentRoute.value.name).toBe('rentals-list')
    expect(router.currentRoute.value.meta.priority).toBe('P0')

    // 4. Transaction Composer
    await router.push('/app/cortex-rental/new')
    expect(router.currentRoute.value.name).toBe('rental-composer')
    expect(router.currentRoute.value.meta.layout).toBe('wizard')

    // 5. Rental Detail
    await router.push('/app/cortex-rental/DEMO-TRX-2026-001')
    expect(router.currentRoute.value.name).toBe('rental-detail')
    expect(router.currentRoute.value.params.name).toBe('DEMO-TRX-2026-001')

    // 6. Check-out Scanner
    await router.push('/app/cortex-checkout/DEMO-TRX-2026-001')
    expect(router.currentRoute.value.name).toBe('checkout-scanner')
    expect(router.currentRoute.value.meta.layout).toBe('warehouse')

    // 7. Check-in Scanner
    await router.push('/app/cortex-checkin/DEMO-TRX-2026-001')
    expect(router.currentRoute.value.name).toBe('checkin-scanner')
    expect(router.currentRoute.value.meta.layout).toBe('warehouse')

    // 8. Approval Queue
    await router.push('/app/cortex-approvals')
    expect(router.currentRoute.value.name).toBe('ai-inbox')
    expect(router.currentRoute.value.query.type).toBe('approval')
    expect(router.currentRoute.value.meta.priority).toBe('P0')

    // 14. Consignment Dashboard
    await router.push('/app/cortex-consignment')
    expect(router.currentRoute.value.name).toBe('consignment-dashboard')
    expect(router.currentRoute.value.meta.priority).toBe('P0')

    // 15. Owner Statement
    await router.push('/app/cortex-owner-statement/DEMO-OWN-001/2026-08')
    expect(router.currentRoute.value.name).toBe('owner-statement')
    expect(router.currentRoute.value.params.owner).toBe('DEMO-OWN-001')
    expect(router.currentRoute.value.params.period).toBe('2026-08')
  }, 180000)

  it('R-TEST-4: Synchronizes Copilot active context with current route and params', async () => {
    const router = createAppRouter(true)
    const copilotStore = useCopilotStore()

    await router.push('/app/cortex-rental/DEMO-TRX-2026-001')
    expect(copilotStore.activeContext.routeName).toBe('rental-detail')
    expect(copilotStore.activeContext.screenId).toBe(5)
    expect(copilotStore.activeContext.entityId).toBe('DEMO-TRX-2026-001')
  })

  it('R-TEST-5: Auth Guard redirects unauthenticated users to /login', async () => {
    const router = createAppRouter(true)
    const sessionStore = useSessionStore()
    sessionStore.logout()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })))

    await router.push('/app/cortex-operations')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/app/cortex-operations')
  })

  it('R-TEST-6: Permission Guard redirects unauthorized user to /permission-denied', async () => {
    const router = createAppRouter(true)
    const sessionStore = useSessionStore()

    // Restrict permissions
    if (sessionStore.currentUser) {
      sessionStore.currentUser.roles = ['Viewer']
      sessionStore.currentUser.permissions = []
    }

    await router.push('/app/cortex-approvals')
    expect(router.currentRoute.value.name).toBe('permission-denied')
    expect(router.currentRoute.value.query.required).toBe('cortex:approvals:decide')
  })
})
