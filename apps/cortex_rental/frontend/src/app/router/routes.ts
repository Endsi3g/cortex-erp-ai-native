import type { RouteRecordRaw } from 'vue-router'
import type { CortexRouteMeta } from './types'
import { useSessionStore } from '@/stores/session'

/**
 * Canonical Cortex route map. The app is served by Frappe under /cortex/
 * (see ROUTER_BASE); every path below is relative to it. This file is also
 * the single source of truth for the navigation rail: a route appears in
 * the rail when it has a `category` and is not `hideInSidebar`.
 */
export const ROUTER_BASE = '/cortex/'

type Meta = Omit<CortexRouteMeta, 'requiresAuth' | 'priority'> & Partial<Pick<CortexRouteMeta, 'requiresAuth' | 'priority'>>

function meta(value: Meta): CortexRouteMeta {
  return { requiresAuth: true, priority: 'P0', ...value } as CortexRouteMeta
}

export const routes: RouteRecordRaw[] = [
  // Home = the conversation (Claude-style). People without assistant access land on Operations.
  {
    path: '/',
    name: 'home',
    component: () => import('@/features/assistant/views/AssistantHomeView.vue'),
    meta: meta({ screenId: 20, titleKey: 'routes.home', layout: 'app', category: 'assistant', iconName: 'Asterisk' }),
    beforeEnter: () => (useSessionStore().hasPermission('cortex:copilot:access') ? true : { name: 'operations-overview' })
  },

  // Operations
  {
    path: '/operations',
    name: 'operations-overview',
    component: () => import('@/features/operations/views/OperationsOverviewView.vue'),
    meta: meta({ screenId: 1, titleKey: 'routes.operations_overview', layout: 'app', requiredPermission: 'cortex:operations:view', category: 'operations', iconName: 'LayoutDashboard' })
  },
  {
    path: '/availability',
    name: 'availability-matrix',
    component: () => import('@/features/availability/views/AvailabilityMatrixView.vue'),
    meta: meta({ screenId: 2, titleKey: 'routes.availability_matrix', layout: 'app', requiredPermission: 'cortex:availability:view', category: 'operations', iconName: 'CalendarRange' })
  },
  {
    path: '/rentals',
    name: 'rentals-list',
    component: () => import('@/features/rentals/views/RentalsListView.vue'),
    meta: meta({ screenId: 3, titleKey: 'routes.rentals_list', layout: 'app', requiredPermission: 'cortex:rental:view', category: 'operations', iconName: 'FileText' })
  },
  {
    path: '/rentals/new',
    name: 'rental-composer',
    component: () => import('@/features/rentals/views/TransactionComposerView.vue'),
    meta: meta({ screenId: 4, titleKey: 'routes.rental_composer', layout: 'wizard', requiredPermission: 'cortex:quote:create', breadcrumbParent: 'rentals-list', hideInSidebar: true })
  },
  {
    path: '/rentals/:name',
    name: 'rental-detail',
    component: () => import('@/features/rentals/views/RentalDetailView.vue'),
    meta: meta({ screenId: 5, titleKey: 'routes.rental_detail', layout: 'app', requiredPermission: 'cortex:rental:view', breadcrumbParent: 'rentals-list', hideInSidebar: true })
  },

  // Warehouse
  {
    path: '/checkout/:rental?',
    name: 'checkout-scanner',
    component: () => import('@/features/checkout/views/CheckoutScannerView.vue'),
    meta: meta({ screenId: 6, titleKey: 'routes.checkout_scanner', layout: 'warehouse', requiredPermission: 'cortex:checkout:perform', category: 'warehouse', iconName: 'PackageMinus' })
  },
  {
    path: '/checkin/:rental?',
    name: 'checkin-scanner',
    component: () => import('@/features/checkin/views/CheckinScannerView.vue'),
    meta: meta({ screenId: 7, titleKey: 'routes.checkin_scanner', layout: 'warehouse', requiredPermission: 'cortex:checkin:perform', category: 'warehouse', iconName: 'PackagePlus' })
  },

  // Customers
  {
    path: '/customers',
    name: 'customers-list',
    component: () => import('@/features/customers/views/CustomersListView.vue'),
    meta: meta({ screenId: 27, titleKey: 'routes.customers_list', layout: 'app', requiredPermission: 'cortex:rental:view', category: 'customers', iconName: 'Users' })
  },
  {
    path: '/customers/:customer',
    name: 'customer-detail',
    component: () => import('@/features/customers/views/CustomerDetailView.vue'),
    meta: meta({ screenId: 28, titleKey: 'routes.customer_detail', layout: 'app', requiredPermission: 'cortex:rental:view', breadcrumbParent: 'customers-list', hideInSidebar: true })
  },

  // Catalog
  {
    path: '/equipment',
    name: 'equipment-list',
    component: () => import('@/features/catalog/views/EquipmentListView.vue'),
    meta: meta({ screenId: 9, titleKey: 'routes.equipment_list', priority: 'P1', layout: 'app', requiredPermission: 'cortex:catalog:view', category: 'catalog', iconName: 'Camera' })
  },
  {
    path: '/equipment/:item',
    name: 'equipment-detail',
    component: () => import('@/features/catalog/views/EquipmentDetailView.vue'),
    meta: meta({ screenId: 10, titleKey: 'routes.equipment_detail', priority: 'P1', layout: 'app', requiredPermission: 'cortex:catalog:view', breadcrumbParent: 'equipment-list', hideInSidebar: true })
  },
  {
    path: '/serials/:serial',
    name: 'serial-detail',
    component: () => import('@/features/catalog/views/SerialDetailView.vue'),
    meta: meta({ screenId: 11, titleKey: 'routes.serial_detail', priority: 'P1', layout: 'app', requiredPermission: 'cortex:serial:view', breadcrumbParent: 'equipment-list', hideInSidebar: true })
  },
  {
    path: '/kits',
    name: 'kits-list',
    component: () => import('@/features/catalog/views/KitsPackagesView.vue'),
    meta: meta({ screenId: 12, titleKey: 'routes.kits_list', priority: 'P2', layout: 'app', requiredPermission: 'cortex:catalog:view', category: 'catalog', iconName: 'Boxes' })
  },

  // Finance
  {
    path: '/finance/profit-and-loss',
    name: 'finance-pnl',
    component: () => import('@/features/finance/views/ProfitAndLossView.vue'),
    meta: meta({ screenId: 29, titleKey: 'routes.finance_pnl', layout: 'app', requiredPermission: 'cortex:finance:view', category: 'finance', iconName: 'ChartLine' })
  },
  {
    path: '/finance/invoices',
    name: 'finance-invoices',
    component: () => import('@/features/finance/views/InvoicesView.vue'),
    meta: meta({ screenId: 30, titleKey: 'routes.finance_invoices', layout: 'app', requiredPermission: 'cortex:finance:view', category: 'finance', iconName: 'Receipt' })
  },
  {
    path: '/consignment',
    name: 'consignment-dashboard',
    component: () => import('@/features/consignment/views/ConsignmentDashboardView.vue'),
    meta: meta({ screenId: 14, titleKey: 'routes.consignment_dashboard', layout: 'app', requiredPermission: 'cortex:consignment:view', category: 'finance', iconName: 'HandCoins' })
  },
  {
    path: '/consignment/owners',
    name: 'consignment-owners',
    component: () => import('@/features/consignment/views/ConsignmentOwnersView.vue'),
    meta: meta({ screenId: 13, titleKey: 'routes.consignment_owners', priority: 'P1', layout: 'app', requiredPermission: 'cortex:consignment:view', breadcrumbParent: 'consignment-dashboard', hideInSidebar: true })
  },
  {
    path: '/consignment/owners/:owner/statement/:period',
    name: 'owner-statement',
    component: () => import('@/features/consignment/views/OwnerStatementView.vue'),
    meta: meta({ screenId: 15, titleKey: 'routes.owner_statement', layout: 'document', requiredPermission: 'cortex:consignment:finance', breadcrumbParent: 'consignment-owners', hideInSidebar: true })
  },

  // Intelligence
  {
    path: '/ai/inbox',
    name: 'ai-inbox',
    component: () => import('@/features/intelligence/views/AiInboxView.vue'),
    meta: meta({ screenId: 25, titleKey: 'routes.ai_inbox', layout: 'app', requiredPermission: 'cortex:copilot:access', category: 'intelligence', iconName: 'Inbox' })
  },
  {
    path: '/ai/workspace/:itemId?',
    name: 'ai-workspace',
    component: () => import('@/features/intelligence/views/AiWorkspaceView.vue'),
    meta: meta({ screenId: 26, titleKey: 'routes.ai_workspace', layout: 'app', requiredPermission: 'cortex:copilot:access', breadcrumbParent: 'ai-inbox', hideInSidebar: true })
  },
  { path: '/assistant', name: 'assistant-full', redirect: to => ({ name: 'home', query: to.query }) },
  {
    path: '/ai/audit',
    name: 'ai-audit',
    component: () => import('@/features/intelligence/views/AiAuditView.vue'),
    meta: meta({ screenId: 18, titleKey: 'routes.ai_audit', priority: 'P1', layout: 'app', requiredPermission: 'cortex:telemetry:admin', category: 'intelligence', iconName: 'Activity' })
  },

  // Administration
  {
    path: '/admin/policies',
    name: 'rental-policies',
    component: () => import('@/features/administration/views/RentalPoliciesView.vue'),
    meta: meta({ screenId: 21, titleKey: 'routes.rental_policies', priority: 'P2', layout: 'app', requiredPermission: 'cortex:policies:view', category: 'admin', iconName: 'Scale' })
  },
  {
    path: '/admin/team',
    name: 'team-roles',
    component: () => import('@/features/administration/views/TeamRolesView.vue'),
    meta: meta({ screenId: 22, titleKey: 'routes.team_roles', priority: 'P2', layout: 'app', requiredPermission: 'cortex:team:manage', category: 'admin', iconName: 'ShieldCheck' })
  },
  {
    path: '/admin/import',
    name: 'import-migration',
    component: () => import('@/features/administration/views/ImportMigrationView.vue'),
    meta: meta({ screenId: 23, titleKey: 'routes.import_migration', priority: 'P1', layout: 'wizard', requiredPermission: 'cortex:migration:run', category: 'admin', iconName: 'Upload' })
  },
  {
    path: '/admin/audit',
    name: 'audit-log',
    component: () => import('@/features/administration/views/AuditLogView.vue'),
    meta: meta({ screenId: 24, titleKey: 'routes.audit_log', priority: 'P1', layout: 'app', requiredPermission: 'cortex:audit:view', category: 'admin', iconName: 'History' })
  },

  // Screens merged into the AI Inbox / AI Audit (HANDOFF V2) — kept as redirects.
  { path: '/approvals', name: 'approval-queue', redirect: { name: 'ai-inbox', query: { type: 'approval' } } },
  { path: '/ai/incoming', name: 'incoming-requests', redirect: { name: 'ai-inbox', query: { type: 'inbound' } } },
  { path: '/ai/drafts', name: 'ai-drafts', redirect: { name: 'ai-inbox', query: { type: 'draft' } } },
  { path: '/ai/activity', name: 'agent-activity', redirect: { name: 'ai-audit' } },
  { path: '/copilot', name: 'copilot-sidebar-view', redirect: { name: 'assistant-full' } },

  // System
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/auth/views/LoginView.vue'),
    meta: meta({ screenId: 0, titleKey: 'routes.login', layout: 'minimal', requiresAuth: false, hideInSidebar: true })
  },
  {
    path: '/permission-denied',
    name: 'permission-denied',
    component: () => import('@/features/common/views/PermissionDeniedView.vue'),
    meta: meta({ screenId: 0, titleKey: 'routes.permission_denied', layout: 'app', hideInSidebar: true })
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/features/common/views/NotFoundView.vue'),
    meta: meta({ screenId: 0, titleKey: 'routes.not_found', layout: 'app', hideInSidebar: true })
  }
]
