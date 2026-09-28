<template>
  <button
    type="button"
    class="cx-btn-secondary inline-flex min-h-[40px] items-center gap-2 px-4 text-sm"
    :disabled="loading"
    @click="$emit('refresh')"
  >
    <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" aria-hidden="true" />
    <span>Actualiser</span>
  </button>
</template>

<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'

defineProps<{ loading?: boolean }>()
defineEmits<{ (e: 'refresh'): void }>()
</script>
