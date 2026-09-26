import { computed, type Component } from 'vue'
import { useRouter, type RouteRecordNormalized } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Activity,
  Asterisk,
  Boxes,
  CalendarRange,
  Camera,
  ChartLine,
  FileText,
  HandCoins,
  History,
  Inbox,
  LayoutDashboard,
  PackageMinus,
  PackagePlus,
  Receipt,
  Scale,
  ShieldCheck,
  Sparkles,
  Upload,
  Users
} from 'lucide-vue-next'
import { useSessionStore } from '@/stores/session'
import type { NavigationCategory } from '@/app/router/types'

const ICONS: Record<string, Component> = {
  Activity,
  Asterisk,
  Boxes,
  CalendarRange,
  Camera,
  ChartLine,
  FileText,
  HandCoins,
  History,
  Inbox,
  LayoutDashboard,
  PackageMinus,
  PackagePlus,
  Receipt,
  Scale,
  ShieldCheck,
  Sparkles,
  Upload,
  Users
}

export const NAV_CATEGORY_ORDER: NavigationCategory[] = [
  'assistant',
  'operations',
  'warehouse',
  'customers',
  'catalog',
  'finance',
  'intelligence',
  'admin'
]

export interface NavItem {
  name: string
  label: string
  path: string
  icon: Component
  category: NavigationCategory
}

export interface NavGroup {
  category: NavigationCategory
  label: string
  items: NavItem[]
}

function isNavRoute(record: RouteRecordNormalized): boolean {
  return Boolean(record.name && record.meta.category && !record.meta.hideInSidebar && !record.redirect)
}

/**
 * Navigation derived from the route table and filtered by the permissions
 * the server returned for this session. A screen the user cannot open is
 * not offered in the rail (the route guard still enforces it).
 */
export function useNavigation() {
  const router = useRouter()
  const session = useSessionStore()
  const { t } = useI18n()

  const items = computed<NavItem[]>(() =>
    router
      .getRoutes()
      .filter(isNavRoute)
      .filter(record => !record.meta.requiredPermission || session.hasPermission(String(record.meta.requiredPermission)))
      .map(record => ({
        name: String(record.name),
        label: t(record.meta.titleKey),
        path: router.resolve({ name: record.name! }).path,
        icon: ICONS[String(record.meta.iconName)] ?? LayoutDashboard,
        category: record.meta.category as NavigationCategory
      }))
  )

  const groups = computed<NavGroup[]>(() =>
    NAV_CATEGORY_ORDER.map(category => ({
      category,
      label: t(`common.navigation_groups.${category}`),
      items: items.value.filter(item => item.category === category)
    })).filter(group => group.items.length > 0)
  )

  return { items, groups }
}
