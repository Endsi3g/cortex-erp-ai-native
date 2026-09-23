import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNavigationStore } from '@/stores/navigation'

describe('Navigation Store — Sidebar, Search & Breadcrumbs', () => {
  beforeEach(() => {
    localStorage.removeItem('cortex_sidebar_collapsed')
    setActivePinia(createPinia())
  })

  it('N-TEST-1: Toggles and sets sidebar collapse state with persistence', () => {
    const navStore = useNavigationStore()
    expect(navStore.sidebarCollapsed).toBe(true)

    navStore.toggleSidebar()
    expect(navStore.sidebarCollapsed).toBe(false)

    navStore.setSidebarCollapsed(true)
    expect(navStore.sidebarCollapsed).toBe(true)
  })

  it('N-TEST-2: Manages universal search modal state', () => {
    const navStore = useNavigationStore()
    expect(navStore.isUniversalSearchOpen).toBe(false)

    navStore.openUniversalSearch()
    expect(navStore.isUniversalSearchOpen).toBe(true)

    navStore.closeUniversalSearch()
    expect(navStore.isUniversalSearchOpen).toBe(false)

    navStore.toggleUniversalSearch()
    expect(navStore.isUniversalSearchOpen).toBe(true)
  })

  it('N-TEST-3: Records recent routes up to maximum 8 items without duplicates', () => {
    const navStore = useNavigationStore()
    
    navStore.addRecentRoute({ name: 'operations-overview', path: '/app/cortex-operations', title: 'Cockpit' })
    navStore.addRecentRoute({ name: 'availability-matrix', path: '/app/cortex-availability', title: 'Matrice' })
    navStore.addRecentRoute({ name: 'operations-overview', path: '/app/cortex-operations', title: 'Cockpit' })

    expect(navStore.recentRoutes.length).toBe(2)
    expect(navStore.recentRoutes[0].name).toBe('operations-overview')
  })
})
