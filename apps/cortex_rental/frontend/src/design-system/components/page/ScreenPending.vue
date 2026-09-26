<template>
  <div class="flex h-full flex-col">
    <PageHeader :title="title" />
    <div class="flex flex-1 items-center justify-center px-6 py-16">
      <div class="max-w-md text-center">
        <p class="text-base font-medium text-ink-gray-8">Écran en cours de reconstruction</p>
        <p class="mt-2 text-p-sm text-ink-gray-5">
          {{ detail }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import PageHeader from './PageHeader.vue'

defineProps<{ title: string; detail: string }>()
</script>
