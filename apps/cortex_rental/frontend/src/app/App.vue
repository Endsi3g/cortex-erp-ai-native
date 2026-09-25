<template>
  <FrappeUIProvider>
    <CompanyProvider>
      <ToastProvider>
        <ModalProvider>
          <RouterView v-if="route.meta.layout === 'minimal'" />
          <AppLayout v-else>
            <RouterView />
          </AppLayout>
        </ModalProvider>
      </ToastProvider>
    </CompanyProvider>
  </FrappeUIProvider>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRoute, RouterView } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'
import { useNavigationStore } from '@/stores/navigation'
import { useCopilotStore } from '@/stores/copilot'
import AppLayout from '@/app/layouts/AppLayout.vue'
import CompanyProvider from '@/app/providers/CompanyProvider.vue'
import ToastProvider from '@/app/providers/ToastProvider.vue'
import ModalProvider from '@/app/providers/ModalProvider.vue'

const route = useRoute()
const navigationStore = useNavigationStore()
const copilotStore = useCopilotStore()

function handleKeyDown(e: KeyboardEvent) {
  const isMeta = e.metaKey || e.ctrlKey
  if (isMeta && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    navigationStore.toggleUniversalSearch()
  } else if (isMeta && e.key.toLowerCase() === 'j') {
    e.preventDefault()
    copilotStore.toggle()
  } else if (e.key === 'Escape' && copilotStore.isOpen && !navigationStore.isUniversalSearchOpen) {
    copilotStore.close()
  }
}

onMounted(() => window.addEventListener('keydown', handleKeyDown))
onUnmounted(() => window.removeEventListener('keydown', handleKeyDown))
</script>
