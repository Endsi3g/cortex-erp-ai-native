<template>
  <div class="cortex-root-inner min-h-[calc(100vh-var(--navbar-height,56px))] bg-white font-sans text-cortex-text-primary antialiased">
    <FrappeUIProvider>
      <CompanyProvider>
        <ToastProvider>
          <ModalProvider>
            <RouterView />
          </ModalProvider>
        </ToastProvider>
      </CompanyProvider>
    </FrappeUIProvider>
  </div>
</template>

<script setup lang="ts">
// The Desk provides the navbar and the workspace sidebar: this root renders the screen only.
import { RouterView } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'
import CompanyProvider from '@/app/providers/CompanyProvider.vue'
import ToastProvider from '@/app/providers/ToastProvider.vue'
import ModalProvider from '@/app/providers/ModalProvider.vue'
</script>
