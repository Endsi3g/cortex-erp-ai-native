<template>
  <slot :active-company="sessionStore.activeCompany" :is-loading="sessionStore.isLoadingSession" />
</template>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
</script>
