<template>
  <slot :active-company="sessionStore.activeCompany" :is-loading="sessionStore.isLoadingSession" />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()

onMounted(async () => {
  if (!sessionStore.activeCompanyId) {
    await sessionStore.initializeSession()
  }
})
</script>
