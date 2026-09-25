<template>
  <!-- ERPNext page head: 46px (45 + 1px border), 16px gutters, 18px semibold title. -->
  <header class="flex h-[46px] shrink-0 items-center justify-between gap-4 border-b border-outline-gray-1 px-4">
    <div class="flex min-w-0 items-center gap-2">
      <slot name="prefix" />
      <h1 class="truncate text-xl font-semibold text-ink-gray-9">{{ title }}</h1>
      <slot name="title-suffix" />
    </div>
    <div class="flex shrink-0 items-center gap-2.5">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ title: string }>()
</script>
