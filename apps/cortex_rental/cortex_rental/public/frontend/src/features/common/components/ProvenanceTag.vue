<template>
  <span
    v-if="label"
    class="inline-flex items-center rounded border border-cortex-border bg-cortex-surface-subtle px-2 py-0.5 text-xs font-medium text-cortex-text-secondary"
    :title="hint"
    data-test="provenance-tag"
  >
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// Only non-production data is labelled: an `api` response needs no badge.
const props = defineProps<{ provenance?: string | null }>()

const labels: Record<string, { label: string; hint: string }> = {
  mock: { label: 'Données simulées', hint: 'Mode Mock: aucune donnée ERPNext réelle.' },
  demo: { label: 'Données de démonstration', hint: 'Jeu de données synthétique.' },
  stale: { label: 'Données périmées', hint: 'La dernière synchronisation est ancienne.' }
}

const entry = computed(() => (props.provenance ? labels[props.provenance] : undefined))
const label = computed(() => entry.value?.label)
const hint = computed(() => entry.value?.hint)
</script>
