<template>
  <div class="cx-page" data-test="screen-native-erp">
    <CortexPageHeader :title="title">
      <template #actions><a :href="href" class="cx-btn-primary">{{ cta }}</a></template>
    </CortexPageHeader>
    <section class="cx-section">
      <p class="m-0 text-sm">{{ description }}</p>
      <p class="mt-2 text-sm" style="color: var(--erp-muted)">
        Cet écran est la vue native, avec ses droits et son historique, plutôt qu'une copie dans Cortex.
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import CortexPageHeader from '../components/CortexPageHeader.vue'

defineProps<{ title: string; description: string; href: string; cta: string }>()
</script>
