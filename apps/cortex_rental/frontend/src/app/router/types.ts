export type LayoutType =
  | 'app'          // Standard desktop sidebar + topbar
  | 'warehouse'    // Scanner layout with high-contrast header & barcode focus
  | 'chat'         // Fullscreen conversational workspace
  | 'document'     // Document review / PDF layout (OwnerStatement)
  | 'wizard'       // Step-by-step transaction composer
  | 'minimal'      // Authentication & standalone errors

export type NavigationCategory =
  | 'operations'
  | 'warehouse'
  | 'customers'
  | 'catalog'
  | 'finance'
  | 'intelligence'
  | 'admin'

export interface CortexRouteMeta extends Record<string | number | symbol, unknown> {
  screenId: number               // Canonical screen ID (0 for system views)
  titleKey: string               // i18n key e.g. "routes.operations"
  priority: 'P0' | 'P1' | 'P2'
  layout: LayoutType
  requiresAuth: boolean
  requiredPermission?: string    // e.g. "cortex:operations:view"
  breadcrumbKey?: string
  breadcrumbParent?: string      // Parent route name for automatic tree building
  hideInSidebar?: boolean
  category?: NavigationCategory
  iconName?: string              // Lucide icon name
  badgeCount?: number | string
}

declare module 'vue-router' {
  interface RouteMeta extends CortexRouteMeta {}
}
