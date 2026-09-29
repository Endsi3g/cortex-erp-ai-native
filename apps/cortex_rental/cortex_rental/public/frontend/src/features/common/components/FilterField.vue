<template>
  <label class="block">
    <span class="sr-only">{{ label }}</span>
    <slot />
  </label>
</template>

<script setup lang="ts">
// Filled field whose visible label is its placeholder (report filters); the label stays for assistive tech.
defineProps<{ label: string }>()
</script>
