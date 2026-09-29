<template>
  <button type="button" class="cx-btn-soft cx-btn-icon" title="Actualiser" aria-label="Actualiser" :disabled="loading" @click="$emit('refresh')">
    <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" aria-hidden="true" />
  </button>
</template>

<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'

defineProps<{ loading?: boolean }>()
defineEmits<{ (e: 'refresh'): void }>()
</script>
