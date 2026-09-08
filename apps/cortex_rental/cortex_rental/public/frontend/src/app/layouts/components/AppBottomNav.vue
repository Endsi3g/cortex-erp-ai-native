<template>
  <!-- Mobile Bottom Navigation Bar (64px / h-16) with 5 Canonical Destinations -->
  <nav
    class="fixed bottom-0 inset-x-0 z-40 h-16 bg-cortex-surface border-t border-cortex-border select-none shadow-lg px-2 flex items-center justify-around font-sans"
    aria-label="Navigation Mobile"
  >
    <!-- 1. Operations Cockpit -->
    <RouterLink
      to="/app/cortex-operations"
      class="flex flex-col items-center justify-center min-w-[56px] min-h-[48px] px-1 py-1 rounded-xl transition-colors group focus:outline-none"
      :class="isActiveRoute('/app/cortex-operations') ? 'text-cortex-primary-600 font-semibold' : 'text-cortex-text-muted hover:text-cortex-text-primary'"
    >
      <div class="relative flex items-center justify-center w-6 h-6">
        <LayoutDashboard class="w-5 h-5" />
        <span
          v-if="isActiveRoute('/app/cortex-operations')"
          class="absolute -bottom-1 w-1.5 h-1.5 rounded-full bg-cortex-primary-600"
        />
      </div>
      <span class="text-[10px] mt-0.5 leading-tight">
        {{ t('common.mobile_tabs.operations') }}
      </span>
    </RouterLink>

    <!-- 2. Rentals Directory -->
    <RouterLink
      to="/app/cortex-rentals"
      class="flex flex-col items-center justify-center min-w-[56px] min-h-[48px] px-1 py-1 rounded-xl transition-colors group focus:outline-none"
      :class="isActiveRoute('/app/cortex-rentals') || isActiveRoute('/app/cortex-rental') ? 'text-cortex-primary-600 font-semibold' : 'text-cortex-text-muted hover:text-cortex-text-primary'"
    >
      <div class="relative flex items-center justify-center w-6 h-6">
        <FileSpreadsheet class="w-5 h-5" />
        <span
          v-if="isActiveRoute('/app/cortex-rentals') || isActiveRoute('/app/cortex-rental')"
          class="absolute -bottom-1 w-1.5 h-1.5 rounded-full bg-cortex-primary-600"
        />
      </div>
      <span class="text-[10px] mt-0.5 leading-tight">
        {{ t('common.mobile_tabs.rentals') }}
      </span>
    </RouterLink>

    <!-- 3. Scan Check-out -->
    <RouterLink
      to="/app/cortex-checkout/DEMO-TRX-2026-006"
      class="flex flex-col items-center justify-center min-w-[56px] min-h-[48px] px-1 py-1 rounded-xl transition-colors group focus:outline-none"
      :class="isActiveRoute('/app/cortex-checkout') ? 'text-cortex-primary-600 font-semibold' : 'text-cortex-text-muted hover:text-cortex-text-primary'"
    >
      <div class="relative flex items-center justify-center w-6 h-6">
        <LogOut class="w-5 h-5" />
        <span
          v-if="isActiveRoute('/app/cortex-checkout')"
          class="absolute -bottom-1 w-1.5 h-1.5 rounded-full bg-cortex-primary-600"
        />
      </div>
      <span class="text-[10px] mt-0.5 leading-tight">
        {{ t('common.mobile_tabs.checkout') }}
      </span>
    </RouterLink>

    <!-- 4. Scan Check-in -->
    <RouterLink
      to="/app/cortex-checkin/DEMO-TRX-2026-001"
      class="flex flex-col items-center justify-center min-w-[56px] min-h-[48px] px-1 py-1 rounded-xl transition-colors group focus:outline-none"
      :class="isActiveRoute('/app/cortex-checkin') ? 'text-cortex-primary-600 font-semibold' : 'text-cortex-text-muted hover:text-cortex-text-primary'"
    >
      <div class="relative flex items-center justify-center w-6 h-6">
        <LogIn class="w-5 h-5" />
        <span
          v-if="isActiveRoute('/app/cortex-checkin')"
          class="absolute -bottom-1 w-1.5 h-1.5 rounded-full bg-cortex-primary-600"
        />
      </div>
      <span class="text-[10px] mt-0.5 leading-tight">
        {{ t('common.mobile_tabs.checkin') }}
      </span>
    </RouterLink>

    <!-- 5. Copilot AI Assistant Trigger -->
    <button
      type="button"
      @click="copilotStore.toggle"
      class="flex flex-col items-center justify-center min-w-[56px] min-h-[48px] px-1 py-1 rounded-xl transition-colors group focus:outline-none"
      :class="copilotStore.isOpen ? 'text-cortex-primary-600 font-semibold' : 'text-cortex-text-muted hover:text-cortex-text-primary'"
      :aria-label="t('common.mobile_tabs.copilot')"
    >
      <div class="relative flex items-center justify-center w-6 h-6">
        <Sparkles class="w-5 h-5" />
        <span
          v-if="copilotStore.unapprovedDraftCount > 0"
          class="absolute -top-1 -right-1 flex items-center justify-center w-3.5 h-3.5 text-[9px] font-bold rounded-full bg-cortex-primary-600 text-white"
        >
          {{ copilotStore.unapprovedDraftCount }}
        </span>
      </div>
      <span class="text-[10px] mt-0.5 leading-tight">
        {{ t('common.mobile_tabs.copilot') }}
      </span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute, RouterLink } from 'vue-router'
import {
  LayoutDashboard,
  FileSpreadsheet,
  LogOut,
  LogIn,
  Sparkles
} from 'lucide-vue-next'
import { useCopilotStore } from '@/stores/copilot'

const { t } = useI18n()
const route = useRoute()
const copilotStore = useCopilotStore()

const isActiveRoute = (pathPrefix: string): boolean => {
  return route.path.startsWith(pathPrefix)
}
</script>
