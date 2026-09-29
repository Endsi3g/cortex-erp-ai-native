import type { Router } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useNavigationStore } from '@/stores/navigation'
import { useCopilotStore } from '@/stores/copilot'
import { i18n } from '@/app/i18n'

const ONBOARDING_PROMPTED = 'cortex_onboarding_prompted'
const AUTH_SCREENS = new Set(['login', 'forgot-password', 'login-link', 'request-access'])

export function setupRouterGuards(router: Router) {
  // 1. Authentication & Session Guard
  router.beforeEach(async (to, _from, next) => {
    const sessionStore = useSessionStore()

    // Sign-in screens: a visitor who already has a session goes straight to the app.
    if (typeof to.name === 'string' && AUTH_SCREENS.has(to.name)) {
      if (sessionStore.isAuthenticated || (await sessionStore.initializeSession())) {
        const redirect = typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/') && !to.query.redirect.startsWith('//') ? to.query.redirect : '/app/cortex-operations'
        return next(redirect)
      }
      return next()
    }
    if (to.meta.requiresAuth && !sessionStore.isAuthenticated && !(await sessionStore.initializeSession())) {
      return next({
        name: 'login',
        query: { redirect: to.fullPath }
      })
    }
    // Guided setup for a company owner (once per browser session; never on the setup screen itself).
    if (sessionStore.isAuthenticated && sessionStore.onboardingNeeded && to.name !== 'onboarding' && typeof window !== 'undefined') {
      try {
        if (!sessionStorage.getItem(ONBOARDING_PROMPTED)) {
          sessionStorage.setItem(ONBOARDING_PROMPTED, '1')
          return next('/app/cortex-company-setup')
        }
      } catch {
        // Storage can be unavailable (private mode): skip the prompt rather than loop.
      }
    }
    next()
  })

  // 2. Multi-Tenant Company Guard
  // 3. RBAC Permission Guard
  router.beforeEach(async (to, _from, next) => {
    const sessionStore = useSessionStore()
    const inboxPermissionByView: Record<string, string> = {
      inbound: 'cortex:intake:view',
      draft: 'cortex:drafts:review',
      approval: 'cortex:approvals:decide'
    }
    const inboxPermission = to.name === 'ai-inbox' && typeof to.query.type === 'string'
      ? inboxPermissionByView[to.query.type]
      : undefined
    const requiredPermission = inboxPermission || to.meta.requiredPermission as string | undefined

    if (requiredPermission && !sessionStore.hasPermission(requiredPermission)) {
      return next({
        name: 'permission-denied',
        query: {
          resource: to.fullPath,
          required: requiredPermission
        }
      })
    }
    next()
  })

  // 4. Dynamic Document Title & i18n Sync
  router.afterEach((to) => {
    const titleKey = to.meta.titleKey || 'common.app_title'
    const pageTitle = i18n.global.t ? i18n.global.t(titleKey) : titleKey
    if (typeof document !== 'undefined') {
      document.title = `${pageTitle} — Cortex OS`
    }
  })

  // 5. Contextual Copilot Route Context Synchronizer
  router.afterEach((to) => {
    const copilotStore = useCopilotStore()
    const entityId = (to.params.name || to.params.rental || to.params.item || to.params.serial || to.params.owner) as string | undefined

    copilotStore.syncRouteContext({
      routeName: String(to.name || 'unnamed-route'),
      path: to.path,
      screenId: to.meta.screenId || 0,
      entityId: entityId || null
    })
  })

  // 6. Navigation Breadcrumbs & Recent History Synchronizer
  router.afterEach((to) => {
    const navigationStore = useNavigationStore()

    // Resolve breadcrumb stack
    const breadcrumbList = [
      { labelKey: 'routes.operations', to: '/app/cortex-operations' }
    ]

    if (to.name !== 'operations-overview') {
      if (to.meta.breadcrumbParent) {
        breadcrumbList.push({
          labelKey: `routes.${to.meta.breadcrumbParent.replace('-', '_')}`,
          to: `/app/cortex-${to.meta.breadcrumbParent.split('-')[0]}`
        })
      }

      breadcrumbList.push({
        labelKey: to.meta.titleKey,
        to: to.path
      })
    }

    navigationStore.setBreadcrumbs(breadcrumbList)

    if (to.name && to.meta.titleKey && to.name !== 'login' && to.name !== 'not-found') {
      const title = i18n.global.t ? i18n.global.t(to.meta.titleKey) : String(to.name)
      navigationStore.addRecentRoute({
        name: String(to.name),
        path: to.path,
        title
      })
    }
  })
}
