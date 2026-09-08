<template>
  <aside
    class="flex flex-col bg-cortex-surface border-r border-cortex-border h-full transition-all duration-200 ease-in-out select-none flex-shrink-0 z-20 font-sans"
    :class="navigationStore.sidebarCollapsed ? 'w-18' : 'w-62'"
    aria-label="Navigation Principale"
  >
    <!-- Brand / Logo Area -->
    <div
      class="h-14 flex items-center border-b border-cortex-border px-3"
      :class="navigationStore.sidebarCollapsed ? 'justify-center' : 'justify-between'"
    >
      <CortexLogo :collapsed="navigationStore.sidebarCollapsed" />
    </div>

    <!-- Navigation Groups Scroll Area -->
    <div class="flex-1 overflow-y-auto py-3 px-2 space-y-4">
      <div
        v-for="group in navGroups"
        :key="group.id"
        class="space-y-0.5"
      >
        <!-- Group Header (Hidden in collapsed mode) -->
        <div
          v-if="!navigationStore.sidebarCollapsed"
          class="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-cortex-text-muted"
        >
          {{ t(group.titleKey) }}
        </div>

        <div
          v-else
          class="h-px bg-cortex-border my-2 mx-1"
          aria-hidden="true"
        />

        <!-- Group Nav Links -->
        <RouterLink
          v-for="item in group.items"
          :key="item.name"
          :to="item.to"
          custom
          v-slot="{ href, navigate, isActive, isExactActive }"
        >
          <a
            :href="href"
            @click="navigate"
            class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-all group relative"
            :class="[
              isActive || isExactActive
                ? 'bg-cortex-primary-50 text-cortex-primary-800 font-semibold border-l-3 border-cortex-primary-600 shadow-2xs'
                : 'text-cortex-text-secondary hover:text-cortex-text-primary hover:bg-cortex-surface-subtle',
              navigationStore.sidebarCollapsed ? 'justify-center' : 'justify-between'
            ]"
            :title="navigationStore.sidebarCollapsed ? t(item.titleKey) : undefined"
          >
            <div class="flex items-center gap-2.5 truncate">
              <component
                :is="item.icon"
                class="w-4 h-4 flex-shrink-0 transition-colors"
                :class="isActive || isExactActive ? 'text-cortex-primary-600' : 'text-cortex-text-muted group-hover:text-cortex-text-primary'"
              />

              <span v-if="!navigationStore.sidebarCollapsed" class="truncate">
                {{ t(item.titleKey) }}
              </span>
            </div>

            <!-- Badge counter (Approvals, Incoming, etc.) -->
            <span
              v-if="item.badgeCount && !navigationStore.sidebarCollapsed"
              class="flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-cortex-primary-100 text-cortex-primary-700 flex-shrink-0"
            >
              {{ item.badgeCount }}
            </span>

            <!-- Badge dot in collapsed mode -->
            <span
              v-if="item.badgeCount && navigationStore.sidebarCollapsed"
              class="absolute top-1 right-1 w-2 h-2 rounded-full bg-cortex-primary-600 ring-2 ring-cortex-surface"
            />
          </a>
        </RouterLink>
      </div>
    </div>

    <!-- Bottom Sidebar Section: Version & Collapse Toggle -->
    <div class="p-2 border-t border-cortex-border bg-cortex-surface-subtle">
      <button
        type="button"
        @click="navigationStore.toggleSidebar"
        class="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs font-medium text-cortex-text-muted hover:text-cortex-text-primary hover:bg-cortex-surface transition-colors"
        :class="navigationStore.sidebarCollapsed ? 'justify-center' : 'justify-between'"
        :aria-label="navigationStore.sidebarCollapsed ? t('common.actions.expand_sidebar') : t('common.actions.collapse_sidebar')"
      >
        <div class="flex items-center gap-2">
          <PanelLeftClose v-if="!navigationStore.sidebarCollapsed" class="w-4 h-4" />
          <PanelLeftOpen v-else class="w-4 h-4" />
          <span v-if="!navigationStore.sidebarCollapsed">
            {{ t('common.actions.collapse_sidebar') }}
          </span>
        </div>
        <span v-if="!navigationStore.sidebarCollapsed" class="font-mono text-[10px] text-cortex-text-muted">
          v1.0
        </span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  LayoutDashboard,
  CalendarRange,
  FileSpreadsheet,
  PlusCircle,
  LogOut,
  LogIn,
  ShieldCheck,
  Percent,
  Users,
  Inbox,
  Sparkles,
  Activity,
  MessageSquareCode,
  Package,
  Barcode,
  Layers,
  Scale,
  ShieldAlert,
  UploadCloud,
  History,
  PanelLeftClose,
  PanelLeftOpen
} from 'lucide-vue-next'
import { useNavigationStore } from '@/stores/navigation'
import CortexLogo from './CortexLogo.vue'

const { t } = useI18n()
const navigationStore = useNavigationStore()

interface NavItem {
  name: string
  to: string
  titleKey: string
  icon: unknown
  badgeCount?: number | string
}

interface NavGroup {
  id: string
  titleKey: string
  items: NavItem[]
}

const navGroups: NavGroup[] = [
  // 1. Operations
  {
    id: 'operations',
    titleKey: 'common.navigation_groups.operations',
    items: [
      { name: 'operations-overview', to: '/app/cortex-operations', titleKey: 'routes.operations_overview', icon: LayoutDashboard },
      { name: 'availability-matrix', to: '/app/cortex-availability', titleKey: 'routes.availability_matrix', icon: CalendarRange },
      { name: 'rentals-list', to: '/app/cortex-rentals', titleKey: 'routes.rentals_list', icon: FileSpreadsheet },
      { name: 'rental-composer', to: '/app/cortex-rental/new', titleKey: 'routes.rental_composer', icon: PlusCircle }
    ]
  },
  // 2. Warehouse & Field
  {
    id: 'warehouse',
    titleKey: 'common.navigation_groups.warehouse',
    items: [
      { name: 'checkout-scanner', to: '/app/cortex-checkout/DEMO-TRX-2026-006', titleKey: 'routes.checkout_scanner', icon: LogOut },
      { name: 'checkin-scanner', to: '/app/cortex-checkin/DEMO-TRX-2026-001', titleKey: 'routes.checkin_scanner', icon: LogIn }
    ]
  },
  // 3. Supervision & Finance
  {
    id: 'supervision',
    titleKey: 'common.navigation_groups.supervision',
    items: [
      { name: 'approval-queue', to: '/app/cortex-approvals', titleKey: 'routes.approval_queue', icon: ShieldCheck, badgeCount: 4 },
      { name: 'consignment-dashboard', to: '/app/cortex-consignment', titleKey: 'routes.consignment_dashboard', icon: Percent },
      { name: 'consignment-owners', to: '/app/cortex-consignment-owner', titleKey: 'routes.consignment_owners', icon: Users }
    ]
  },
  // 4. Intelligence
  {
    id: 'intelligence',
    titleKey: 'common.navigation_groups.intelligence',
    items: [
      { name: 'incoming-requests', to: '/app/cortex-incoming', titleKey: 'routes.incoming_requests', icon: Inbox, badgeCount: 3 },
      { name: 'ai-drafts', to: '/app/cortex-ai-drafts', titleKey: 'routes.ai_drafts', icon: Sparkles },
      { name: 'agent-activity', to: '/app/cortex-agent-activity', titleKey: 'routes.agent_activity', icon: Activity },
      { name: 'assistant-full', to: '/app/cortex-assistant', titleKey: 'routes.assistant_full', icon: MessageSquareCode }
    ]
  },
  // 5. Catalog & Fleet
  {
    id: 'catalog',
    titleKey: 'common.navigation_groups.catalog',
    items: [
      { name: 'equipment-list', to: '/app/cortex-equipment', titleKey: 'routes.equipment_list', icon: Package },
      { name: 'serial-detail', to: '/app/cortex-serial/DEMO-SN-ALX-001', titleKey: 'routes.serial_detail', icon: Barcode },
      { name: 'kits-list', to: '/app/cortex-kits', titleKey: 'routes.kits_list', icon: Layers }
    ]
  },
  // 6. Administration
  {
    id: 'admin',
    titleKey: 'common.navigation_groups.admin',
    items: [
      { name: 'rental-policies', to: '/app/cortex-rental-policy', titleKey: 'routes.rental_policies', icon: Scale },
      { name: 'team-roles', to: '/app/cortex-team', titleKey: 'routes.team_roles', icon: ShieldAlert },
      { name: 'import-migration', to: '/app/cortex-import', titleKey: 'routes.import_migration', icon: UploadCloud },
      { name: 'audit-log', to: '/app/cortex-audit-event', titleKey: 'routes.audit_log', icon: History }
    ]
  }
]
</script>
