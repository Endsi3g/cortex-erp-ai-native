<template>
  <header class="flex flex-col gap-4 pb-4 border-b border-cortex-border sm:flex-row sm:items-start sm:justify-between">
    <div class="min-w-0">
      <div class="flex flex-wrap items-center gap-2">
        <h1 class="text-2xl font-semibold tracking-tight text-cortex-text-primary">{{ title }}</h1>
        <ProvenanceTag :provenance="provenance" />
      </div>
      <p v-if="subtitle" class="mt-1 text-sm text-cortex-text-secondary">{{ subtitle }}</p>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
import ProvenanceTag from './ProvenanceTag.vue'

defineProps<{ title: string; subtitle?: string; provenance?: string | null }>()
</script>
