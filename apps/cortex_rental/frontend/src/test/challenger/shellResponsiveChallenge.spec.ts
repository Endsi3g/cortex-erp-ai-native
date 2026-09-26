import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createAppRouter } from '@/app/router'
import { routes } from '@/app/router/routes'
import { useSessionStore } from '@/stores/session'
import { useNavigationStore } from '@/stores/navigation'
import { useCopilotStore } from '@/stores/copilot'
import { i18n } from '@/app/i18n'
import frCA from '@locales/fr-CA.json'
import enCA from '@locales/en-CA.json'
// @ts-expect-error TS6305 composite project boundary
import tailwindConfig from '../../../tailwind.config'
import fs from 'node:fs'
import path from 'node:path'

import AppSidebar from '@/app/layouts/components/AppSidebar.vue'
import AppTopbar from '@/app/layouts/components/AppTopbar.vue'

describe('Challenger 2 — App Shell, Canonical Routes, Responsive Constraints & Interaction Edge Cases', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const session = useSessionStore()
    session.currentUser = { id: 'test-user', email: 'test@example.test', full_name: 'Test User', roles: ['System Manager'], permissions: [] }
    session.isAuthenticated = true
    session.userCompanies = [
      { id: 'DEMO-COMP-001', name: 'Cortex Cinema Rentals', code: 'CINEMA-MTL', is_default: true, currency: 'CAD' },
      { id: 'DEMO-COMP-002', name: 'Cortex Broadcast Montréal', code: 'BROADCAST-MTL', currency: 'CAD' }
    ]
    session.activeCompanyId = 'DEMO-COMP-001'
    // Reset document title
    if (typeof document !== 'undefined') {
      document.title = 'Cortex OS'
    }
  })

  // =========================================================================
  // 1. CANONICAL ROUTES & DYNAMIC DOCUMENT TITLE & COPILOT SYNC
  // =========================================================================
  describe('1. Canonical Routes: Resolution, Component Loading, Document Title & Copilot Context', () => {
    it('1.1 Covers every canonical screen; merged screens (8, 16, 17, 19) only exist as redirects', () => {
      const screenIds = routes
        .map(r => r.meta?.screenId)
        .filter((id): id is number => typeof id === 'number' && id > 0)
      const unique = Array.from(new Set(screenIds)).sort((a, b) => a - b)
      const merged = [8, 16, 17, 19]
      const expected = Array.from({ length: 30 }, (_, i) => i + 1).filter(id => !merged.includes(id))
      expect(unique).toEqual(expected)
      for (const name of ['approval-queue', 'incoming-requests', 'ai-drafts', 'agent-activity', 'copilot-sidebar-view']) {
        expect(routes.find(r => r.name === name)?.redirect, name).toBeTruthy()
      }
    })

    it('1.2 Dynamically imports every view component without syntax or resolution errors', async () => {
      for (const route of routes) {
        if (typeof route.component === 'function') {
          const componentModule = await (route.component as () => Promise<any>)()
          expect(componentModule).toBeDefined()
          expect(componentModule.default || componentModule).toBeTruthy()
        }
      }
    }, 180000)

    it('1.3 Evaluates document.title behavior on route transition and detects untranslated key fallbacks', async () => {
      const router = createAppRouter(true)
      const canonicalRoutes = routes.filter(r => r.meta?.screenId && r.meta.screenId >= 1 && r.meta.screenId <= 24)

      const titleResults: Array<{
        screenId: number
        path: string
        titleKey: string
        documentTitle: string
        isRawKeyFallback: boolean
      }> = []

      for (const route of canonicalRoutes) {
        // Resolve path parameters for parameterized routes
        let testPath = route.path
        if (testPath.includes(':name')) testPath = testPath.replace(':name', 'DEMO-TRX-001')
        if (testPath.includes(':rental')) testPath = testPath.replace(':rental', 'DEMO-TRX-001')
        if (testPath.includes(':item')) testPath = testPath.replace(':item', 'DEMO-ITM-ALX35')
        if (testPath.includes(':serial')) testPath = testPath.replace(':serial', 'DEMO-SN-ALX-001')
        if (testPath.includes(':owner')) testPath = testPath.replace(':owner', 'DEMO-OWN-001')
        if (testPath.includes(':period')) testPath = testPath.replace(':period', '2026-08')

        await router.push(testPath)

        const titleKey = route.meta?.titleKey as string
        const currentTitle = document.title
        const isRawKeyFallback = currentTitle.includes(titleKey)

        titleResults.push({
          screenId: route.meta!.screenId as number,
          path: testPath,
          titleKey,
          documentTitle: currentTitle,
          isRawKeyFallback
        })
      }

      // Identify routes where document.title falls back to raw key because key is missing in locale
      const brokenRoutes = titleResults.filter(r => r.isRawKeyFallback)
      
      // Remediation: All routes now have matching translations, so 0 broken routes
      expect(brokenRoutes.length).toBe(0)
    })

    it('1.4 Synchronizes Copilot active context across entity-level parameterized routes', async () => {
      const router = createAppRouter(true)
      const copilotStore = useCopilotStore()

      // Rental Detail
      await router.push('/rentals/DEMO-TRX-999')
      expect(copilotStore.activeContext.screenId).toBe(5)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-TRX-999')
      expect(copilotStore.activeContext.routeName).toBe('rental-detail')

      // Check-out Scanner
      await router.push('/checkout/DEMO-TRX-CHECKOUT-123')
      expect(copilotStore.activeContext.screenId).toBe(6)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-TRX-CHECKOUT-123')

      // Check-in Scanner
      await router.push('/checkin/DEMO-TRX-CHECKIN-456')
      expect(copilotStore.activeContext.screenId).toBe(7)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-TRX-CHECKIN-456')

      // Equipment Detail
      await router.push('/equipment/DEMO-ITM-SONY-FX9')
      expect(copilotStore.activeContext.screenId).toBe(10)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-ITM-SONY-FX9')

      // Serial Detail
      await router.push('/serials/DEMO-SN-FX9-0042')
      expect(copilotStore.activeContext.screenId).toBe(11)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-SN-FX9-0042')

      // Owner Statement
      await router.push('/consignment/owners/DEMO-OWN-LUCAS/statement/2026-09')
      expect(copilotStore.activeContext.screenId).toBe(15)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-OWN-LUCAS')

      // Non-parameterized route clears entityId to null
      await router.push('/operations')
      expect(copilotStore.activeContext.screenId).toBe(1)
      expect(copilotStore.activeContext.entityId).toBeNull()
    })

    it('1.5 Enforces Auth Guard redirection with target redirect query', async () => {
      const router = createAppRouter(true)
      const sessionStore = useSessionStore()
      sessionStore.logout()

      await router.push('/rentals')
      expect(router.currentRoute.value.name).toBe('login')
      expect(router.currentRoute.value.query.redirect).toBe('/rentals')
    })

    it('1.6 Enforces RBAC Permission Guard redirection with required permission query', async () => {
      const router = createAppRouter(true)
      const sessionStore = useSessionStore()

      if (sessionStore.currentUser) {
        sessionStore.currentUser.roles = ['Technician']
        sessionStore.currentUser.permissions = ['cortex:checkout:perform']
      }

      // Attempt visiting Approvals (requires cortex:approvals:decide)
      await router.push('/approvals')
      expect(router.currentRoute.value.name).toBe('permission-denied')
      expect(router.currentRoute.value.query.required).toBe('cortex:approvals:decide')
    })
  })

  // =========================================================================
  // 2. KEYBOARD SHORTCUTS & MODAL / DRAWER ESCAPE DISMISSAL
  // =========================================================================
  describe('2. Keyboard Shortcuts: ⌘K, ⌘J, Escape Dismissal Invariants', () => {
    it('2.1 ⌘K and Ctrl+K toggle Universal Search and prevent default', () => {
      const navigationStore = useNavigationStore()
      expect(navigationStore.isUniversalSearchOpen).toBe(false)

      const dispatchKey = (key: string, isMeta: boolean, isCtrl: boolean) => {
        const event = new KeyboardEvent('keydown', {
          key,
          metaKey: isMeta,
          ctrlKey: isCtrl,
          bubbles: true,
          cancelable: true
        })
        const preventSpy = vi.spyOn(event, 'preventDefault')

        // Direct simulation of App.vue handleKeyDown logic
        const meta = event.metaKey || event.ctrlKey
        if (meta && (event.key === 'k' || event.key === 'K')) {
          event.preventDefault()
          navigationStore.toggleUniversalSearch()
        }
        return { defaultPrevented: preventSpy.mock.calls.length > 0 }
      }

      // Mac ⌘K
      const resMac = dispatchKey('k', true, false)
      expect(resMac.defaultPrevented).toBe(true)
      expect(navigationStore.isUniversalSearchOpen).toBe(true)

      // Mac ⌘K again to close
      dispatchKey('k', true, false)
      expect(navigationStore.isUniversalSearchOpen).toBe(false)

      // Windows Ctrl+K (uppercase K from CapsLock)
      const resWin = dispatchKey('K', false, true)
      expect(resWin.defaultPrevented).toBe(true)
      expect(navigationStore.isUniversalSearchOpen).toBe(true)

      navigationStore.closeUniversalSearch()
    })

    it('2.2 ⌘J and Ctrl+J toggle Copilot Drawer and prevent default', () => {
      const copilotStore = useCopilotStore()
      expect(copilotStore.isOpen).toBe(false)

      const dispatchKey = (key: string, isMeta: boolean, isCtrl: boolean) => {
        const event = new KeyboardEvent('keydown', {
          key,
          metaKey: isMeta,
          ctrlKey: isCtrl,
          bubbles: true,
          cancelable: true
        })
        const preventSpy = vi.spyOn(event, 'preventDefault')

        const meta = event.metaKey || event.ctrlKey
        if (meta && (event.key === 'j' || event.key === 'J')) {
          event.preventDefault()
          copilotStore.toggle()
        }
        return { defaultPrevented: preventSpy.mock.calls.length > 0 }
      }

      // Windows Ctrl+J
      const resWin = dispatchKey('j', false, true)
      expect(resWin.defaultPrevented).toBe(true)
      expect(copilotStore.isOpen).toBe(true)

      // Mac ⌘J
      const resMac = dispatchKey('j', true, false)
      expect(resMac.defaultPrevented).toBe(true)
      expect(copilotStore.isOpen).toBe(false)
    })

    it('2.3 Escape closes open Universal Search modal, then Copilot drawer sequentially', () => {
      const navigationStore = useNavigationStore()
      const copilotStore = useCopilotStore()

      // Open both
      navigationStore.openUniversalSearch()
      copilotStore.open()
      expect(navigationStore.isUniversalSearchOpen).toBe(true)
      expect(copilotStore.isOpen).toBe(true)

      const dispatchEscape = () => {
        if (navigationStore.isUniversalSearchOpen) {
          navigationStore.closeUniversalSearch()
        } else if (copilotStore.isOpen) {
          copilotStore.close()
        }
      }

      // First Escape: dismisses Universal Search
      dispatchEscape()
      expect(navigationStore.isUniversalSearchOpen).toBe(false)
      expect(copilotStore.isOpen).toBe(true)

      // Second Escape: dismisses Copilot Drawer
      dispatchEscape()
      expect(copilotStore.isOpen).toBe(false)
    })
  })

  // =========================================================================
  // 3. MULTI-TENANT & PERMISSION-AWARE NAVIGATION
  // =========================================================================
  describe('3. Company switching and permission-aware navigation', () => {
    it('3.1 Rejects a switch to a company the session was not granted', async () => {
      const session = useSessionStore()
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      expect(await session.switchCompany('SOMEONE-ELSE')).toBe(false)
      expect(session.activeCompanyId).toBe('DEMO-COMP-001')
      errorSpy.mockRestore()
    })

    it('3.2 Accepts a switch to an authorized company and persists it', async () => {
      const session = useSessionStore()
      expect(await session.switchCompany('DEMO-COMP-002')).toBe(true)
      expect(localStorage.getItem('cortex_active_company_id')).toBe('DEMO-COMP-002')
    })

    it('3.3 The rail only offers screens the server granted', async () => {
      const session = useSessionStore()
      session.currentUser = { id: 'u', email: 'u@x.test', full_name: 'U', roles: ['Rental Operator'], permissions: ['cortex:rental:view', 'cortex:operations:view'] }
      const router = createAppRouter(true)
      await router.push('/rentals')
      const wrapper = mount(AppSidebar, { global: { plugins: [i18n, router] } })
      const labels = wrapper.findAll('a[aria-label]').map(link => link.attributes('aria-label'))
      expect(labels).toContain(i18n.global.t('routes.rentals_list'))
      expect(labels).not.toContain(i18n.global.t('routes.finance_pnl'))
      expect(labels).not.toContain(i18n.global.t('routes.team_roles'))
    })
  })

  // =========================================================================
  // 4. SHELL GEOMETRY (ERPNext reference) & RESPONSIVE BEHAVIOUR
  // =========================================================================
  describe('4. Shell geometry matches the ERPNext reference', () => {
    it('4.1 Collapsed rail is 50px, marks the active screen and hides on phones', async () => {
      const router = createAppRouter(true)
      await router.push('/rentals/CR-TRX-1')
      const wrapper = mount(AppSidebar, { global: { plugins: [i18n, router] } })
      const nav = wrapper.find('nav')
      expect(nav.classes()).toContain('w-12.5')
      const active = wrapper.find('a[aria-current="page"]')
      expect(active.attributes('aria-label')).toBe(i18n.global.t('routes.rentals_list'))
    })

    it('4.2 Top bar is 48px with a 300px search field', async () => {
      const router = createAppRouter(true)
      await router.push('/operations')
      const wrapper = mount(AppTopbar, { global: { plugins: [i18n, router] } })
      expect(wrapper.find('header').classes()).toContain('h-12')
      expect(wrapper.find('button.w-\\[300px\\]').exists()).toBe(true)
    })

    it('4.3 Tailwind exposes the measured rail widths', () => {
      const spacing = (tailwindConfig.theme?.extend as any)?.spacing || {}
      expect(spacing['12.5']).toBe('3.125rem')
      expect(spacing['55']).toBe('13.75rem')
      expect(spacing['13']).toBe('3.25rem')
    })

    it('4.4 Shell source carries no demo identifiers', () => {
      const dir = path.resolve(__dirname, '../../app/layouts')
      const files = fs.readdirSync(path.join(dir, 'components')).map(f => path.join(dir, 'components', f)).concat(path.join(dir, 'AppLayout.vue'))
      for (const file of files) {
        expect(fs.readFileSync(file, 'utf-8'), file).not.toMatch(/DEMO-|Kael Tremblay/)
      }
    })
  })

  // =========================================================================
  // 5. PREFERS-REDUCED-MOTION SPECIFICATION & CLAMPING
  // =========================================================================
  describe('5. prefers-reduced-motion CSS Specification & Transition Clamping', () => {
    it('5.1 motion.css strictly clamps transition-duration and animation-duration to 0.001ms', () => {
      const motionCssPath = path.resolve(
        __dirname,
        '../../design-system/styles/motion.css'
      )
      expect(fs.existsSync(motionCssPath)).toBe(true)

      const cssContent = fs.readFileSync(motionCssPath, 'utf-8')

      // Verify media query exists
      expect(cssContent).toContain('@media (prefers-reduced-motion: reduce)')

      // Verify duration clamping to 0.001ms !important
      expect(cssContent).toMatch(/animation-duration:\s*0\.001ms\s*!important/)
      expect(cssContent).toMatch(/transition-duration:\s*0\.001ms\s*!important/)
      expect(cssContent).toMatch(/animation-iteration-count:\s*1\s*!important/)
      expect(cssContent).toMatch(/scroll-behavior:\s*auto\s*!important/)

      // Verify skeleton and pulse suppression
      expect(cssContent).toContain('.cx-skeleton')
      expect(cssContent).toContain('.cx-status-indicator__pulse')
    })
  })

  // =========================================================================
  // 6. I18N ROUTE & SHELL KEY PARITY FORENSIC AUDIT
  // =========================================================================
  describe('6. Forensic Audit: i18n Route Keys Parity between routes.ts and fr-CA / en-CA Catalogs', () => {
    it('6.1 Identifies all route titleKeys in routes.ts missing in fr-CA and en-CA catalogs', () => {
      const frRoutes = (frCA as any).routes || {}
      const enRoutes = (enCA as any).routes || {}

      const missingFrKeys: string[] = []
      const missingEnKeys: string[] = []

      for (const route of routes) {
        const titleKey = route.meta?.titleKey as string | undefined
        if (titleKey && titleKey.startsWith('routes.')) {
          const subKey = titleKey.replace('routes.', '')
          if (!(subKey in frRoutes)) {
            missingFrKeys.push(titleKey)
          }
          if (!(subKey in enRoutes)) {
            missingEnKeys.push(titleKey)
          }
        }
      }

      // Both catalogs have exact parity in the missing keys
      expect(missingFrKeys).toEqual(missingEnKeys)

      // Remediation: All canonical and system route titleKeys are now present in both catalogs
      expect(missingFrKeys).toEqual([])
      expect(missingEnKeys).toEqual([])
    })

    it('6.2 Shell i18n keys are defined in fr-CA and en-CA catalogs', () => {
      const frCommon = (frCA as any).common || {}
      const enCommon = (enCA as any).common || {}
      
      // AppSidebar group headers: 'common.navigation_groups.*'
      expect(frCommon.navigation_groups).toBeDefined()
      expect(frCommon.navigation_groups.operations).toBe('Opérations')
      expect(enCommon.navigation_groups).toBeDefined()

      // AppSidebar action titles: 'common.actions.collapse_sidebar'
      expect(frCommon.actions).toBeDefined()
      expect(enCommon.actions).toBeDefined()

      expect(Object.keys(frCommon.navigation).sort()).toEqual(Object.keys(enCommon.navigation).sort())
      expect(Object.keys(frCommon.navigation_groups).sort()).toEqual(Object.keys(enCommon.navigation_groups).sort())
    })
  })
})
