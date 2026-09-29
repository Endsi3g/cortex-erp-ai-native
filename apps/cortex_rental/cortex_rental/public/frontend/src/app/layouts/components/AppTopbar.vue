<template>
  <header
    class="h-14 bg-cortex-surface border-b border-cortex-border sticky top-0 z-30 flex items-center justify-between px-4 font-sans select-none shadow-xs"
  >
    <!-- Left Section: Sidebar Toggle & Breadcrumbs -->
    <div class="flex items-center gap-3 min-w-0">
      <button
        type="button"
        @click="navigationStore.toggleSidebar"
        class="p-1.5 rounded-lg text-cortex-text-muted hover:text-cortex-text-primary hover:bg-cortex-surface-subtle transition-colors focus:outline-none focus:ring-2 focus:ring-cortex-primary-500"
        :title="navigationStore.sidebarCollapsed ? t('common.actions.expand_sidebar') : t('common.actions.collapse_sidebar')"
        :aria-label="navigationStore.sidebarCollapsed ? t('common.actions.expand_sidebar') : t('common.actions.collapse_sidebar')"
      >
        <Menu v-if="navigationStore.sidebarCollapsed" class="w-4 h-4" />
        <PanelLeftClose v-else class="w-4 h-4" />
      </button>

      <!-- Dynamic Breadcrumbs -->
      <CortexBreadcrumbs class="hidden sm:flex" />
    </div>

    <!-- Center Section: Universal Search Trigger -->
    <div class="flex items-center justify-center flex-1 max-w-md mx-4">
      <UniversalSearch />
    </div>

    <!-- Right Section: Actions, Badges & Profile -->
    <div class="flex items-center gap-2 flex-shrink-0">
      <!-- Multi-Tenant Company Selector -->
      <CompanySelector />

      <!-- AI Inbox badge includes pending human reviews -->
      <RouterLink
        to="/app/cortex-ai-inbox"
        class="relative p-1.5 rounded-lg text-cortex-text-muted hover:text-cortex-text-primary hover:bg-cortex-surface-subtle transition-colors focus:outline-none focus:ring-2 focus:ring-cortex-primary-500"
        :title="t('routes.ai_inbox')"
        :aria-label="t('routes.ai_inbox')"
      >
        <ShieldCheck class="w-4 h-4" />
        <span
          v-if="(approvalsStore.pendingCount ?? 0) > 0"
          class="absolute -top-1 -right-1 flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-amber-500 text-white shadow-xs"
        >
          {{ approvalsStore.pendingCount }}
        </span>
      </RouterLink>

      <!-- Copilot Trigger Button (⌘J) -->
      <CopilotTrigger />

      <!-- Language Toggle FR / EN -->
      <LocaleSwitcher />

      <!-- Account menu: profile, Desk, sign out -->
      <div class="pl-1 border-l border-cortex-border ml-1">
        <UserMenu />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { Menu, PanelLeftClose, ShieldCheck } from 'lucide-vue-next'
import { useNavigationStore } from '@/stores/navigation'
import { useApprovalsStore } from '@/stores/approvals'
import CortexBreadcrumbs from './CortexBreadcrumbs.vue'
import UniversalSearch from './UniversalSearch.vue'
import CompanySelector from './CompanySelector.vue'
import CopilotTrigger from './CopilotTrigger.vue'
import LocaleSwitcher from './LocaleSwitcher.vue'
import UserMenu from './UserMenu.vue'

const { t } = useI18n()
const navigationStore = useNavigationStore()
const approvalsStore = useApprovalsStore()
onMounted(() => {
  void approvalsStore.fetchPendingApprovals()
})
</script>
