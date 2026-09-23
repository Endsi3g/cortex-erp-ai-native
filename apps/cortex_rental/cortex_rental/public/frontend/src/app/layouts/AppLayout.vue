<template>
  <div class="flex h-screen w-screen overflow-hidden bg-[#f7f8f8] text-cortex-text-primary font-sans antialiased">
    <!-- Desktop Collapsible Sidebar -->
    <AppSidebar class="hidden md:flex" />

    <!-- Main Workspace Container -->
    <div class="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
      <!-- Desktop Topbar (56px) -->
      <AppTopbar />

      <!-- Main Scrollable Feature Canvas -->
      <main
        class="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-6 bg-[#f7f8f8] focus:outline-none"
        tabindex="-1"
        id="main-content"
      >
        <slot>
          <RouterView v-slot="{ Component }">
            <Transition name="fade" mode="out-in">
              <component :is="Component" />
            </Transition>
          </RouterView>
        </slot>
      </main>
    </div>

    <!-- Non-modal Contextual Copilot Drawer (416px, ⌘J) -->
    <CopilotDrawer />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import AppTopbar from './components/AppTopbar.vue'
import CopilotDrawer from './components/CopilotDrawer.vue'
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 120ms cubic-bezier(0.16, 1, 0.3, 1);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
