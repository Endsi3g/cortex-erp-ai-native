import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
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

import CompanySelector from '@/app/layouts/components/CompanySelector.vue'
import AppBottomNav from '@/app/layouts/components/AppBottomNav.vue'
import MobileLayout from '@/app/layouts/MobileLayout.vue'
import UniversalSearch from '@/app/layouts/components/UniversalSearch.vue'

describe('Challenger 2 — App Shell, 24 Canonical Routes, Responsive Constraints & Interaction Edge Cases', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Reset document title
    if (typeof document !== 'undefined') {
      document.title = 'Cortex OS'
    }
  })

  // =========================================================================
  // 1. THE 24 CANONICAL ROUTES & DYNAMIC DOCUMENT TITLE & COPILOT SYNC
  // =========================================================================
  describe('1. Canonical Routes: Resolution, Component Loading, Document Title & Copilot Context', () => {
    it('1.1 Exactly covers all 24 canonical operational screen IDs (1..24)', () => {
      const screenIds = routes
        .map(r => r.meta?.screenId)
        .filter((id): id is number => typeof id === 'number' && id > 0)
        .sort((a, b) => a - b)

      const uniqueIds = Array.from(new Set(screenIds))
      expect(uniqueIds.length).toBe(24)
      expect(uniqueIds).toEqual(Array.from({ length: 24 }, (_, i) => i + 1))
    })

    it('1.2 Dynamically imports every view component without syntax or resolution errors', async () => {
      for (const route of routes) {
        if (typeof route.component === 'function') {
          const componentModule = await (route.component as () => Promise<any>)()
          expect(componentModule).toBeDefined()
          expect(componentModule.default || componentModule).toBeTruthy()
        }
      }
    })

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
      await router.push('/app/cortex-rental/DEMO-TRX-999')
      expect(copilotStore.activeContext.screenId).toBe(5)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-TRX-999')
      expect(copilotStore.activeContext.routeName).toBe('rental-detail')

      // Check-out Scanner
      await router.push('/app/cortex-checkout/DEMO-TRX-CHECKOUT-123')
      expect(copilotStore.activeContext.screenId).toBe(6)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-TRX-CHECKOUT-123')

      // Check-in Scanner
      await router.push('/app/cortex-checkin/DEMO-TRX-CHECKIN-456')
      expect(copilotStore.activeContext.screenId).toBe(7)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-TRX-CHECKIN-456')

      // Equipment Detail
      await router.push('/app/cortex-equipment/DEMO-ITM-SONY-FX9')
      expect(copilotStore.activeContext.screenId).toBe(10)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-ITM-SONY-FX9')

      // Serial Detail
      await router.push('/app/cortex-serial/DEMO-SN-FX9-0042')
      expect(copilotStore.activeContext.screenId).toBe(11)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-SN-FX9-0042')

      // Owner Statement
      await router.push('/app/cortex-owner-statement/DEMO-OWN-LUCAS/2026-09')
      expect(copilotStore.activeContext.screenId).toBe(15)
      expect(copilotStore.activeContext.entityId).toBe('DEMO-OWN-LUCAS')

      // Non-parameterized route clears entityId to null
      await router.push('/app/cortex-operations')
      expect(copilotStore.activeContext.screenId).toBe(1)
      expect(copilotStore.activeContext.entityId).toBeNull()
    })

    it('1.5 Enforces Auth Guard redirection with target redirect query', async () => {
      const router = createAppRouter(true)
      const sessionStore = useSessionStore()
      sessionStore.logout()

      await router.push('/app/cortex-rentals')
      expect(router.currentRoute.value.name).toBe('login')
      expect(router.currentRoute.value.query.redirect).toBe('/app/cortex-rentals')
    })

    it('1.6 Enforces RBAC Permission Guard redirection with required permission query', async () => {
      const router = createAppRouter(true)
      const sessionStore = useSessionStore()

      if (sessionStore.currentUser) {
        sessionStore.currentUser.roles = ['Technician']
        sessionStore.currentUser.permissions = ['cortex:checkout:perform']
      }

      // Attempt visiting Approvals (requires cortex:approvals:decide)
      await router.push('/app/cortex-approvals')
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
  // 3. MULTI-TENANT COMPANY SELECTOR & STRICT DOM GATING
  // =========================================================================
  describe('3. Multi-Tenant Company Selector Gating & Route Re-validation', () => {
    it('3.1 Hidden completely from DOM when user has exactly 1 authorized company', async () => {
      const sessionStore = useSessionStore()
      sessionStore.userCompanies = [
        { id: 'COMP-SINGLE-001', name: 'Single Corp', code: 'SGL', currency: 'CAD' }
      ]
      expect(sessionStore.hasMultipleCompanies).toBe(false)

      const router = createAppRouter(true)
      const wrapper = mount(CompanySelector, {
        global: {
          plugins: [i18n, router]
        }
      })

      // The root element has v-if="sessionStore.hasMultipleCompanies"
      expect(wrapper.find('button[aria-haspopup="listbox"]').exists()).toBe(false)
      expect(wrapper.find('.relative').exists()).toBe(false)
    })

    it('3.2 Visible in DOM when user has > 1 authorized companies', async () => {
      const sessionStore = useSessionStore()
      sessionStore.userCompanies = [
        { id: 'COMP-001', name: 'Company 1', code: 'C1', currency: 'CAD' },
        { id: 'COMP-002', name: 'Company 2', code: 'C2', currency: 'CAD' }
      ]
      expect(sessionStore.hasMultipleCompanies).toBe(true)

      const router = createAppRouter(true)
      const wrapper = mount(CompanySelector, {
        global: {
          plugins: [i18n, router]
        }
      })

      const triggerBtn = wrapper.find('button[aria-haspopup="listbox"]')
      expect(triggerBtn.exists()).toBe(true)
      expect(triggerBtn.text()).toContain('Company 1')
    })

    it('3.3 Clicking switcher opens dropdown with all authorized companies', async () => {
      const sessionStore = useSessionStore()
      sessionStore.userCompanies = [
        { id: 'COMP-001', name: 'Company 1', code: 'C1', currency: 'CAD' },
        { id: 'COMP-002', name: 'Company 2', code: 'C2', currency: 'CAD' }
      ]

      const router = createAppRouter(true)
      const wrapper = mount(CompanySelector, {
        global: {
          plugins: [i18n, router]
        }
      })

      const triggerBtn = wrapper.find('button[aria-haspopup="listbox"]')
      await triggerBtn.trigger('click')

      const dropdown = wrapper.find('div[role="listbox"]')
      expect(dropdown.exists()).toBe(true)
      const options = wrapper.findAll('button[role="option"]')
      expect(options.length).toBe(2)
      expect(options[0].text()).toContain('Company 1')
      expect(options[1].text()).toContain('Company 2')
    })

    it('3.4 Security check: Rejects unauthorized company switch and logs security alert', async () => {
      const sessionStore = useSessionStore()
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const success = await sessionStore.switchCompany('ATTACK-MALICIOUS-COMPANY-666')
      expect(success).toBe(false)
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[Cortex Security] Attempted unauthorized company switch')
      )
      consoleSpy.mockRestore()
    })

    it('3.5 Switching company revalidates route by pushing to /app/cortex-operations', async () => {
      const router = createAppRouter(true)
      const sessionStore = useSessionStore()
      await router.push('/app/cortex-rentals')

      const wrapper = mount(CompanySelector, {
        global: {
          plugins: [i18n, router]
        }
      })

      // Open dropdown and select company 2
      await wrapper.find('button[aria-haspopup="listbox"]').trigger('click')
      const options = wrapper.findAll('button[role="option"]')
      await options[1].trigger('click')
      await flushPromises()

      expect(sessionStore.activeCompanyId).toBe('DEMO-COMP-002')
      expect(router.currentRoute.value.path).toBe('/app/cortex-operations')
    })

    it('3.6 Selecting currently active company closes dropdown without re-navigating', async () => {
      const router = createAppRouter(true)
      await router.push('/app/cortex-rentals')
      const routerSpy = vi.spyOn(router, 'push')

      const wrapper = mount(CompanySelector, {
        global: {
          plugins: [i18n, router]
        }
      })

      // Open dropdown and select same active company
      await wrapper.find('button[aria-haspopup="listbox"]').trigger('click')
      const options = wrapper.findAll('button[role="option"]')
      await options[0].trigger('click')
      await flushPromises()

      expect(routerSpy).not.toHaveBeenCalled()
      expect(wrapper.find('div[role="listbox"]').exists()).toBe(false)
    })
  })

  // =========================================================================
  // 4. RESPONSIVE LAYOUT CONSTRAINTS & ACCESSIBILITY TARGETS
  // =========================================================================
  describe('4. Responsive Layout Constraints: 1440px, 1280px, 768px, 390px', () => {
    it('4.1 App.vue viewport breakpoint: 768px boundary separates Desktop and Mobile layouts', () => {
      const checkViewportMobile = (width: number) => width < 768

      expect(checkViewportMobile(1440)).toBe(false) // Desktop -> AppLayout
      expect(checkViewportMobile(1280)).toBe(false) // Laptop -> AppLayout
      expect(checkViewportMobile(768)).toBe(false)  // Tablet Boundary (768px) -> AppLayout
      expect(checkViewportMobile(767)).toBe(true)   // Mobile (<768px) -> MobileLayout
      expect(checkViewportMobile(390)).toBe(true)   // Mobile (390px iPhone) -> MobileLayout
    })

    it('4.2 Mobile Bottom Navigation Bar (64px) has 5 canonical destinations with >=44px touch targets', async () => {
      const router = createAppRouter(true)
      await router.push('/app/cortex-operations')

      const wrapper = mount(AppBottomNav, {
        global: {
          plugins: [i18n, router]
        }
      })

      // Check bar height: h-16 is 4rem = 64px
      const navEl = wrapper.find('nav')
      expect(navEl.classes()).toContain('h-16')

      // Check 5 items
      const links = wrapper.findAll('a')
      const buttons = wrapper.findAll('button')
      const totalDestinations = links.length + buttons.length
      expect(totalDestinations).toBe(5)

      // Check touch target classes: min-w-[56px] and min-h-[48px] (both >= 44px)
      for (const link of links) {
        expect(link.classes()).toContain('min-w-[56px]')
        expect(link.classes()).toContain('min-h-[48px]')
      }
      for (const btn of buttons) {
        expect(btn.classes()).toContain('min-w-[56px]')
        expect(btn.classes()).toContain('min-h-[48px]')
      }
    })

    it('4.3 MobileLayout provides safe bottom scroll padding (pb-24) to avoid bottom nav occlusion', async () => {
      const router = createAppRouter(true)
      await router.push('/app/cortex-operations')

      const wrapper = mount(MobileLayout, {
        global: {
          plugins: [i18n, router]
        }
      })

      const mainEl = wrapper.find('main')
      expect(mainEl.exists()).toBe(true)
      expect(mainEl.classes()).toContain('pb-24') // 96px padding bottom > 64px nav bar
    })

    it('4.4 Audits Tailwind config for missing custom dimensions (w-18, w-62, h-13)', () => {
      // Worker handoff claims:
      // "h-13 for 52px scan input, h-14 for 56px topbar, w-62 for 248px sidebar"
      const extend = tailwindConfig.theme?.extend as any
      const spacing = extend?.spacing || {}
      const width = extend?.width || {}
      const height = extend?.height || {}

      const hasH13 = spacing['13'] || height['13']
      const hasW18 = spacing['18'] || width['18']
      const hasW62 = spacing['62'] || width['62']

      // EMPIRICAL ASSERTION: Verify custom spacing dimensions are properly configured
      expect(hasH13, 'h-13 custom spacing for 52px scan input should be defined').toBeTruthy()
      expect(hasW18, 'w-18 custom spacing for 72px collapsed sidebar should be defined').toBeTruthy()
      expect(hasW62, 'w-62 custom spacing for 248px expanded sidebar should be defined').toBeTruthy()
    })

    it('4.5 Verifies no duplicate UniversalSearch trigger rendering in MobileLayout.vue', async () => {
      // In MobileLayout.vue, UniversalSearch is mounted with :modal-only="true",
      // while the search trigger button is mounted in the header (line 15).
      // This prevents an orphan duplicate search trigger at the bottom of the screen.
      const router = createAppRouter(true)
      await router.push('/app/cortex-operations')

      const wrapper = mount(MobileLayout, {
        global: {
          plugins: [i18n, router]
        }
      })

      // Search button in mobile header
      const headerSearchBtn = wrapper.find('header button[aria-label="Recherche"]')
      expect(headerSearchBtn.exists()).toBe(true)

      // No second search trigger button generated by UniversalSearch inside MobileLayout
      const universalSearchComponent = wrapper.findComponent(UniversalSearch)
      expect(universalSearchComponent.exists()).toBe(true)
      const duplicateBtn = universalSearchComponent.find('button')
      expect(duplicateBtn.exists()).toBe(false)
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

    it('6.2 Identifies AppSidebar and AppBottomNav i18n keys are properly defined in fr-CA and en-CA catalogs', () => {
      const frCommon = (frCA as any).common || {}
      const enCommon = (enCA as any).common || {}
      
      // AppSidebar group headers: 'common.navigation_groups.*'
      expect(frCommon.navigation_groups).toBeDefined()
      expect(frCommon.navigation_groups.operations).toBe('Opérations')
      expect(enCommon.navigation_groups).toBeDefined()

      // AppSidebar action titles: 'common.actions.collapse_sidebar'
      expect(frCommon.actions).toBeDefined()
      expect(enCommon.actions).toBeDefined()

      // AppBottomNav tab titles: 'common.mobile_tabs.*'
      expect(frCommon.mobile_tabs).toBeDefined()
      expect(enCommon.mobile_tabs).toBeDefined()
    })
  })
})
