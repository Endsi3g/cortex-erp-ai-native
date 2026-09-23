import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  // Root Redirect
  {
    path: '/',
    redirect: '/app/cortex-operations'
  },

  // 1. Operations Overview [Screen 1 - P0]
  {
    path: '/app/cortex-operations',
    name: 'operations-overview',
    component: () => import('@/features/operations/views/OperationsOverviewView.vue'),
    meta: {
      screenId: 1,
      titleKey: 'routes.operations_overview',
      priority: 'P0',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:operations:view',
      category: 'operations',
      iconName: 'LayoutDashboard'
    }
  },

  // 2. Availability Matrix [Screen 2 - P0]
  {
    path: '/app/cortex-availability',
    name: 'availability-matrix',
    component: () => import('@/features/availability/views/AvailabilityMatrixView.vue'),
    meta: {
      screenId: 2,
      titleKey: 'routes.availability_matrix',
      priority: 'P0',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:availability:view',
      category: 'operations',
      iconName: 'CalendarRange'
    }
  },

  // 3. Rentals List [Screen 3 - P0]
  {
    path: '/app/cortex-rentals',
    name: 'rentals-list',
    component: () => import('@/features/rentals/views/RentalsListView.vue'),
    meta: {
      screenId: 3,
      titleKey: 'routes.rentals_list',
      priority: 'P0',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:rental:view',
      category: 'operations',
      iconName: 'FileSpreadsheet'
    }
  },

  // 4. Transaction Composer [Screen 4 - P0]
  {
    path: '/app/cortex-rental/new',
    name: 'rental-composer',
    component: () => import('@/features/rentals/views/TransactionComposerView.vue'),
    meta: {
      screenId: 4,
      titleKey: 'routes.rental_composer',
      priority: 'P0',
      layout: 'wizard',
      requiresAuth: true,
      requiredPermission: 'cortex:quote:create',
      category: 'operations',
      iconName: 'PlusCircle'
    }
  },

  // 5. Rental Transaction Detail [Screen 5 - P0]
  {
    path: '/app/cortex-rental/:name',
    name: 'rental-detail',
    component: () => import('@/features/rentals/views/RentalDetailView.vue'),
    meta: {
      screenId: 5,
      titleKey: 'routes.rental_detail',
      priority: 'P0',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:rental:view',
      category: 'operations',
      breadcrumbParent: 'rentals-list',
      hideInSidebar: true,
      iconName: 'FileText'
    }
  },

  // 6. Check-out Scanner [Screen 6 - P0]
  {
    path: '/app/cortex-checkout/:rental',
    name: 'checkout-scanner',
    component: () => import('@/features/checkout/views/CheckoutScannerView.vue'),
    meta: {
      screenId: 6,
      titleKey: 'routes.checkout_scanner',
      priority: 'P0',
      layout: 'warehouse',
      requiresAuth: true,
      requiredPermission: 'cortex:checkout:perform',
      category: 'warehouse',
      iconName: 'LogOut'
    }
  },

  // 7. Check-in Scanner [Screen 7 - P0]
  {
    path: '/app/cortex-checkin/:rental',
    name: 'checkin-scanner',
    component: () => import('@/features/checkin/views/CheckinScannerView.vue'),
    meta: {
      screenId: 7,
      titleKey: 'routes.checkin_scanner',
      priority: 'P0',
      layout: 'warehouse',
      requiresAuth: true,
      requiredPermission: 'cortex:checkin:perform',
      category: 'warehouse',
      iconName: 'LogIn'
    }
  },

  // Approval Queue now lives as a filtered view in AI Inbox.
  {
    path: '/app/cortex-approvals',
    name: 'approval-queue',
    redirect: { name: 'ai-inbox', query: { type: 'approval' } },
    meta: { screenId: 8, titleKey: 'routes.approval_queue', priority: 'P0', layout: 'app', requiresAuth: true, requiredPermission: 'cortex:approvals:decide', hideInSidebar: true }
  },

  // 9. Equipment List [Screen 9 - P1]
  {
    path: '/app/cortex-equipment',
    name: 'equipment-list',
    component: () => import('@/features/catalog/views/EquipmentListView.vue'),
    meta: {
      screenId: 9,
      titleKey: 'routes.equipment_list',
      priority: 'P1',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:catalog:view',
      category: 'catalog',
      iconName: 'Package'
    }
  },

  // 10. Equipment Detail [Screen 10 - P1]
  {
    path: '/app/cortex-equipment/:item',
    name: 'equipment-detail',
    component: () => import('@/features/catalog/views/EquipmentDetailView.vue'),
    meta: {
      screenId: 10,
      titleKey: 'routes.equipment_detail',
      priority: 'P1',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:catalog:view',
      category: 'catalog',
      breadcrumbParent: 'equipment-list',
      hideInSidebar: true,
      iconName: 'PackageSearch'
    }
  },

  // 11. Serial Number Detail [Screen 11 - P1]
  {
    path: '/app/cortex-serial/:serial',
    name: 'serial-detail',
    component: () => import('@/features/catalog/views/SerialDetailView.vue'),
    meta: {
      screenId: 11,
      titleKey: 'routes.serial_detail',
      priority: 'P1',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:serial:view',
      category: 'catalog',
      breadcrumbParent: 'equipment-list',
      hideInSidebar: true,
      iconName: 'Barcode'
    }
  },

  // 12. Kits & Accessories [Screen 12 - P2]
  {
    path: '/app/cortex-kits',
    name: 'kits-list',
    component: () => import('@/features/catalog/views/KitsPackagesView.vue'),
    meta: {
      screenId: 12,
      titleKey: 'routes.kits_list',
      priority: 'P2',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:catalog:manage',
      category: 'catalog',
      iconName: 'Layers'
    }
  },

  // 13. Consignment Owners [Screen 13 - P1]
  {
    path: '/app/cortex-consignment-owner',
    name: 'consignment-owners',
    component: () => import('@/features/consignment/views/ConsignmentOwnersView.vue'),
    meta: {
      screenId: 13,
      titleKey: 'routes.consignment_owners',
      priority: 'P1',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:consignment:view',
      category: 'supervision',
      iconName: 'Users'
    }
  },

  // 14. Consignment Dashboard [Screen 14 - P0]
  {
    path: '/app/cortex-consignment',
    name: 'consignment-dashboard',
    component: () => import('@/features/consignment/views/ConsignmentDashboardView.vue'),
    meta: {
      screenId: 14,
      titleKey: 'routes.consignment_dashboard',
      priority: 'P0',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:consignment:view',
      category: 'supervision',
      iconName: 'Percent'
    }
  },

  // 15. Owner Statement (Safe / Zero PII) [Screen 15 - P0]
  {
    path: '/app/cortex-owner-statement/:owner/:period',
    name: 'owner-statement',
    component: () => import('@/features/consignment/views/OwnerStatementView.vue'),
    meta: {
      screenId: 15,
      titleKey: 'routes.owner_statement',
      priority: 'P0',
      layout: 'document',
      requiresAuth: true,
      requiredPermission: 'cortex:consignment:finance',
      category: 'supervision',
      breadcrumbParent: 'consignment-dashboard',
      hideInSidebar: true,
      iconName: 'FileCheck'
    }
  },

  // 16. Incoming Requests [Screen 16 - P1]
  {
    path: '/app/cortex-incoming',
    name: 'incoming-requests',
    redirect: { name: 'ai-inbox', query: { type: 'inbound' } },
    meta: { screenId: 16, titleKey: 'routes.incoming_requests', priority: 'P1', layout: 'app', requiresAuth: true, requiredPermission: 'cortex:intake:view', hideInSidebar: true }
  },

  // 17. AI Drafts [Screen 17 - P1]
  {
    path: '/app/cortex-ai-drafts',
    name: 'ai-drafts',
    redirect: { name: 'ai-inbox', query: { type: 'draft' } },
    meta: { screenId: 17, titleKey: 'routes.ai_drafts', priority: 'P1', layout: 'app', requiresAuth: true, requiredPermission: 'cortex:drafts:review', hideInSidebar: true }
  },

  // 18. Agent Activity & Telemetry [Screen 18 - P1]
  {
    path: '/app/cortex-agent-activity',
    name: 'agent-activity',
    redirect: { name: 'ai-audit' },
    meta: { screenId: 18, titleKey: 'routes.agent_activity', priority: 'P1', layout: 'app', requiresAuth: true, requiredPermission: 'cortex:telemetry:admin', hideInSidebar: true }
  },

  {
    path: '/app/cortex-ai-inbox',
    name: 'ai-inbox',
    component: () => import('@/features/intelligence/views/AiInboxView.vue'),
    meta: { screenId: 25, titleKey: 'routes.ai_inbox', priority: 'P0', layout: 'app', requiresAuth: true, requiredPermission: 'cortex:copilot:access', category: 'intelligence', iconName: 'Inbox' }
  },
  {
    path: '/app/cortex-ai-workspace/:itemId?',
    name: 'ai-workspace',
    component: () => import('@/features/intelligence/views/AiWorkspaceView.vue'),
    meta: { screenId: 26, titleKey: 'routes.ai_workspace', priority: 'P0', layout: 'app', requiresAuth: true, requiredPermission: 'cortex:copilot:access', category: 'intelligence', iconName: 'Sparkles' }
  },
  {
    path: '/app/cortex-ai-audit',
    name: 'ai-audit',
    component: () => import('@/features/intelligence/views/AiAuditView.vue'),
    meta: { screenId: 27, titleKey: 'routes.ai_audit', priority: 'P1', layout: 'app', requiresAuth: true, requiredPermission: 'cortex:audit:view', category: 'intelligence', iconName: 'Activity' }
  },

  // 19. Copilot Sidebar (Screen 19 - P0) — alias / dedicated route
  {
    path: '/app/cortex-copilot',
    name: 'copilot-sidebar-view',
    component: () => import('@/features/copilot/views/FullAssistantView.vue'),
    meta: {
      screenId: 19,
      titleKey: 'routes.copilot_sidebar',
      priority: 'P0',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:copilot:access',
      category: 'intelligence',
      hideInSidebar: true,
      iconName: 'Sparkles'
    }
  },

  // 20. Full Assistant Page [Screen 20 - P2]
  {
    path: '/app/cortex-assistant',
    name: 'assistant-full',
    component: () => import('@/features/copilot/views/FullAssistantView.vue'),
    meta: {
      screenId: 20,
      titleKey: 'routes.assistant_full',
      priority: 'P2',
      layout: 'chat',
      requiresAuth: true,
      requiredPermission: 'cortex:copilot:access',
      category: 'intelligence',
      iconName: 'MessageSquareCode'
    }
  },

  // 21. Rental Policies [Screen 21 - P2]
  {
    path: '/app/cortex-rental-policy',
    name: 'rental-policies',
    component: () => import('@/features/administration/views/RentalPoliciesView.vue'),
    meta: {
      screenId: 21,
      titleKey: 'routes.rental_policies',
      priority: 'P2',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:policies:view',
      category: 'admin',
      iconName: 'Scale'
    }
  },

  // 22. Team & Roles [Screen 22 - P2]
  {
    path: '/app/cortex-team',
    name: 'team-roles',
    component: () => import('@/features/administration/views/TeamRolesView.vue'),
    meta: {
      screenId: 22,
      titleKey: 'routes.team_roles',
      priority: 'P2',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:team:manage',
      category: 'admin',
      iconName: 'ShieldAlert'
    }
  },

  // 23. Import & Migration Wizard [Screen 23 - P1]
  {
    path: '/app/cortex-import',
    name: 'import-migration',
    component: () => import('@/features/administration/views/ImportMigrationView.vue'),
    meta: {
      screenId: 23,
      titleKey: 'routes.import_migration',
      priority: 'P1',
      layout: 'wizard',
      requiresAuth: true,
      requiredPermission: 'cortex:migration:run',
      category: 'admin',
      iconName: 'UploadCloud'
    }
  },

  // 24. Audit Log [Screen 24 - P1]
  {
    path: '/app/cortex-audit-event',
    name: 'audit-log',
    component: () => import('@/features/administration/views/AuditLogView.vue'),
    meta: {
      screenId: 24,
      titleKey: 'routes.audit_log',
      priority: 'P1',
      layout: 'app',
      requiresAuth: true,
      requiredPermission: 'cortex:audit:view',
      category: 'admin',
      iconName: 'History'
    }
  },

  // System & Utility Routes
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/auth/views/LoginView.vue'),
    meta: {
      screenId: 0,
      titleKey: 'routes.login',
      priority: 'P0',
      layout: 'minimal',
      requiresAuth: false,
      hideInSidebar: true
    }
  },
  {
    path: '/permission-denied',
    name: 'permission-denied',
    component: () => import('@/features/common/views/PermissionDeniedView.vue'),
    meta: {
      screenId: 0,
      titleKey: 'routes.permission_denied',
      priority: 'P0',
      layout: 'minimal',
      requiresAuth: false,
      hideInSidebar: true
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/features/common/views/NotFoundView.vue'),
    meta: {
      screenId: 0,
      titleKey: 'routes.not_found',
      priority: 'P0',
      layout: 'minimal',
      requiresAuth: false,
      hideInSidebar: true
    }
  }
]
