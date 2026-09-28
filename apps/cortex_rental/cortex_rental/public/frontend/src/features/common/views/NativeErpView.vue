<template>
  <div class="mx-auto max-w-2xl space-y-6" data-test="screen-native-erp">
    <CortexPageHeader :title="title" />
    <p class="text-base text-cortex-text-primary">{{ description }}</p>
    <p class="text-sm text-cortex-text-secondary">
      ERPNext reste le système de référence: cet écran est la vue native, avec ses droits et son historique, plutôt qu'une copie dans Cortex.
    </p>
    <a :href="href" class="cx-btn-primary inline-flex min-h-[40px] items-center px-4 text-sm font-medium">{{ cta }}</a>
  </div>
</template>

<script setup lang="ts">
import CortexPageHeader from '../components/CortexPageHeader.vue'

defineProps<{ title: string; description: string; href: string; cta: string }>()
</script>
