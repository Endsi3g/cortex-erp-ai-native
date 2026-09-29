<template>
  <header>
    <div class="cx-titlebar">
      <div class="cx-titlebar__lead">
        <h1>{{ title }}</h1>
        <ProvenanceTag :provenance="provenance" />
      </div>
      <div class="cx-actions">
        <slot name="actions" />
      </div>
    </div>
    <p v-if="subtitle" class="cx-caption">{{ subtitle }}</p>
  </header>
</template>

<script setup lang="ts">
// report title bar: title on the left, actions on the right (see cortex-erp.css).
import ProvenanceTag from './ProvenanceTag.vue'

defineProps<{ title: string; subtitle?: string; provenance?: string | null }>()
</script>
