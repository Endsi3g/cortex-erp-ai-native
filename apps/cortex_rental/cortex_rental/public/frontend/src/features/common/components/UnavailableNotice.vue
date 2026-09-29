<template>
  <div class="rounded-lg border border-cortex-border bg-cortex-surface p-6" role="status" data-test="unavailable-notice">
    <h2 class="text-base font-semibold text-cortex-text-primary">Fonction indisponible</h2>
    <p class="mt-1 text-sm text-cortex-text-secondary">{{ message }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ message: string }>()
</script>
