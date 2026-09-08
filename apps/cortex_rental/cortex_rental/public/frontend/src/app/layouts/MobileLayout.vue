<template>
  <div class="flex flex-col min-h-screen w-screen overflow-x-hidden bg-cortex-bg text-cortex-text-primary font-sans antialiased">
    <!-- Mobile Topbar (64px / h-16) -->
    <header class="h-16 sticky top-0 z-30 bg-cortex-surface border-b border-cortex-border flex items-center justify-between px-3 shadow-xs">
      <!-- Logo -->
      <CortexLogo :collapsed="true" />

      <!-- Center / Company badge if multiple -->
      <div class="flex items-center gap-1.5 max-w-[140px] truncate">
        <CompanySelector />
      </div>

      <!-- Right Actions: Search, Locale, Copilot -->
      <div class="flex items-center gap-1.5">
        <button
          type="button"
          @click="navigationStore.openUniversalSearch"
          class="p-2 rounded-lg text-cortex-text-muted hover:text-cortex-text-primary hover:bg-cortex-surface-subtle"
          aria-label="Recherche"
        >
          <Search class="w-4 h-4" />
        </button>

        <LocaleSwitcher />
      </div>
    </header>

    <!-- Mobile Scrollable Main Content -->
    <main
      class="flex-1 overflow-y-auto p-3.5 pb-24 bg-cortex-bg focus:outline-none"
      id="mobile-main-content"
    >
      <slot>
        <RouterView v-slot="{ Component }">
          <component :is="Component" />
        </RouterView>
      </slot>
    </main>

    <!-- Mobile Bottom Navigation Bar (64px) -->
    <AppBottomNav />

    <!-- Copilot Drawer Modal for Mobile -->
    <CopilotDrawer />

    <!-- Universal Search Modal -->
    <UniversalSearch :modal-only="true" />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { useNavigationStore } from '@/stores/navigation'
import CortexLogo from './components/CortexLogo.vue'
import CompanySelector from './components/CompanySelector.vue'
import LocaleSwitcher from './components/LocaleSwitcher.vue'
import AppBottomNav from './components/AppBottomNav.vue'
import CopilotDrawer from './components/CopilotDrawer.vue'
import UniversalSearch from './components/UniversalSearch.vue'

const navigationStore = useNavigationStore()
</script>
