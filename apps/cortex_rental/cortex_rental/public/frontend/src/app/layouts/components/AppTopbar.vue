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

      <!-- Approvals Badge Counter -->
      <RouterLink
        to="/app/cortex-approvals"
        class="relative p-1.5 rounded-lg text-cortex-text-muted hover:text-cortex-text-primary hover:bg-cortex-surface-subtle transition-colors focus:outline-none focus:ring-2 focus:ring-cortex-primary-500"
        :title="t('routes.approvals')"
        :aria-label="t('routes.approvals')"
      >
        <ShieldCheck class="w-4 h-4" />
        <span
          v-if="approvalsStore.pendingCount > 0"
          class="absolute -top-1 -right-1 flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-amber-500 text-white shadow-xs"
        >
          {{ approvalsStore.pendingCount }}
        </span>
      </RouterLink>

      <!-- Copilot Trigger Button (⌘J) -->
      <CopilotTrigger />

      <!-- Language Toggle FR / EN -->
      <LocaleSwitcher />

      <!-- User Profile Avatar & Role -->
      <div class="flex items-center gap-2 pl-1 border-l border-cortex-border ml-1">
        <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-cortex-ink-900 text-white text-xs font-semibold shadow-xs">
          {{ userInitials }}
        </div>
        <div class="hidden lg:flex flex-col text-left">
          <span class="text-xs font-semibold text-cortex-text-primary leading-tight">
            {{ sessionStore.currentUser?.full_name || 'Utilisateur Cortex' }}
          </span>
          <span class="text-[10px] text-cortex-text-muted leading-tight">
            {{ primaryRole }}
          </span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { Menu, PanelLeftClose, ShieldCheck } from 'lucide-vue-next'
import { useSessionStore } from '@/stores/session'
import { useNavigationStore } from '@/stores/navigation'
import { useApprovalsStore } from '@/stores/approvals'
import CortexBreadcrumbs from './CortexBreadcrumbs.vue'
import UniversalSearch from './UniversalSearch.vue'
import CompanySelector from './CompanySelector.vue'
import CopilotTrigger from './CopilotTrigger.vue'
import LocaleSwitcher from './LocaleSwitcher.vue'

const { t } = useI18n()
const sessionStore = useSessionStore()
const navigationStore = useNavigationStore()
const approvalsStore = useApprovalsStore()

const userInitials = computed(() => {
  const name = sessionStore.currentUser?.full_name || 'Kael Tremblay'
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase()
})

const primaryRole = computed(() => {
  return sessionStore.currentUser?.roles[0] || 'Operations Manager'
})
</script>
