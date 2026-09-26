<template>
  <!-- ERPNext report filter area: 24px gutters, 6-column grid, 16px column / 20px row gaps, 28px controls. -->
  <section
    class="grid grid-cols-1 gap-x-4 gap-y-5 px-6 pt-[15px] sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6"
    :aria-label="label"
  >
    <slot />
  </section>
</template>

<script setup lang="ts">
defineProps<{ label: string }>()
</script>
