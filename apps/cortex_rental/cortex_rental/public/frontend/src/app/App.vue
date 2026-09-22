<template>
  <FrappeUIProvider>
    <CompanyProvider>
      <ToastProvider>
        <ModalProvider>
          <component :is="resolvedLayout">
            <RouterView />
          </component>
        </ModalProvider>
      </ToastProvider>
    </CompanyProvider>
  </FrappeUIProvider>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, RouterView } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'
import { useNavigationStore } from '@/stores/navigation'
import { useCopilotStore } from '@/stores/copilot'
import AppLayout from '@/app/layouts/AppLayout.vue'
import MobileLayout from '@/app/layouts/MobileLayout.vue'
import CompanyProvider from '@/app/providers/CompanyProvider.vue'
import ToastProvider from '@/app/providers/ToastProvider.vue'
import ModalProvider from '@/app/providers/ModalProvider.vue'

const route = useRoute()
const navigationStore = useNavigationStore()
const copilotStore = useCopilotStore()

const isMobile = ref(false)

const checkViewport = () => {
  if (typeof window !== 'undefined') {
    isMobile.value = window.innerWidth < 768
  }
}

const resolvedLayout = computed(() => {
  // If explicitly minimal layout (e.g. login, permission denied)
  if (route.meta.layout === 'minimal') {
    return 'div'
  }

  // Mobile viewport (< 768px) uses MobileLayout
  if (isMobile.value) {
    return MobileLayout
  }

  // Default Desktop / Tablet uses AppLayout
  return AppLayout
})

const handleKeyDown = (e: KeyboardEvent) => {
  const isMeta = e.metaKey || e.ctrlKey

  // ⌘K or Ctrl+K -> Universal Search
  if (isMeta && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    navigationStore.toggleUniversalSearch()
  }

  // ⌘J or Ctrl+J -> Copilot Sidebar Drawer
  if (isMeta && (e.key === 'j' || e.key === 'J')) {
    e.preventDefault()
    copilotStore.toggle()
  }

  // Escape -> Close modal & copilot drawer
  if (e.key === 'Escape') {
    if (navigationStore.isUniversalSearchOpen) {
      navigationStore.closeUniversalSearch()
    } else if (copilotStore.isOpen) {
      copilotStore.close()
    }
  }
}

onMounted(() => {
  checkViewport()
  window.addEventListener('resize', checkViewport)
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkViewport)
  window.removeEventListener('keydown', handleKeyDown)
})
</script>
