import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface BreadcrumbItem {
  labelKey?: string
  label?: string
  to?: string
}

export interface RecentRoute {
  name: string
  path: string
  title: string
  timestamp: number
}

export const useNavigationStore = defineStore('navigation', () => {
  // Sidebar state persisted in localStorage
  const sidebarCollapsed = ref<boolean>(
    typeof localStorage === 'undefined' || localStorage.getItem('cortex_sidebar_collapsed') !== 'false'
  )

  // Mobile bottom navigation active tab
  const activeMobileTab = ref<string>('operations')

  // Dynamic breadcrumbs stack
  const breadcrumbs = ref<BreadcrumbItem[]>([])

  // Recent navigation history
  const recentRoutes = ref<RecentRoute[]>([])

  // Universal search modal visibility
  const isUniversalSearchOpen = ref<boolean>(false)

  // Actions
  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cortex_sidebar_collapsed', String(sidebarCollapsed.value))
    }
  }

  const setSidebarCollapsed = (collapsed: boolean) => {
    sidebarCollapsed.value = collapsed
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cortex_sidebar_collapsed', String(collapsed))
    }
  }

  const setActiveMobileTab = (tab: string) => {
    activeMobileTab.value = tab
  }

  const setBreadcrumbs = (items: BreadcrumbItem[]) => {
    breadcrumbs.value = items
  }

  const addRecentRoute = (route: Omit<RecentRoute, 'timestamp'>) => {
    const filtered = recentRoutes.value.filter(r => r.path !== route.path)
    filtered.unshift({
      ...route,
      timestamp: Date.now()
    })
    // Keep maximum 8 recent routes
    recentRoutes.value = filtered.slice(0, 8)
  }

  const openUniversalSearch = () => {
    isUniversalSearchOpen.value = true
  }

  const closeUniversalSearch = () => {
    isUniversalSearchOpen.value = false
  }

  const toggleUniversalSearch = () => {
    isUniversalSearchOpen.value = !isUniversalSearchOpen.value
  }

  return {
    sidebarCollapsed,
    activeMobileTab,
    breadcrumbs,
    recentRoutes,
    isUniversalSearchOpen,
    toggleSidebar,
    setSidebarCollapsed,
    setActiveMobileTab,
    setBreadcrumbs,
    addRecentRoute,
    openUniversalSearch,
    closeUniversalSearch,
    toggleUniversalSearch
  }
})
