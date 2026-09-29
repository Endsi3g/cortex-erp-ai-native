<template>
  <div class="cxa">
    <main class="cxa__panel">
      <div class="cxa__form">
        <img class="cxa__logo cxa__logo--light" :src="LOGO_LIGHT" alt="Cortex" />
        <img class="cxa__logo cxa__logo--dark" :src="LOGO_DARK" alt="" aria-hidden="true" />
        <h1 class="cxa__title" data-test="auth-title">{{ title }}</h1>
        <p v-if="lead" class="cxa__lead">{{ lead }}</p>
        <slot />
      </div>
    </main>

    <aside class="cxa__aside" aria-label="Présentation">
      <div class="cxa__flutes" aria-hidden="true" />
      <div class="cxa__aside-inner">
        <p class="cxa__eyebrow">Cortex</p>
        <p class="cxa__statement">Toute votre activité opérationnelle, dans un seul poste de travail.</p>
        <div class="cxa__illustration" aria-hidden="true">
          <div v-for="flow in flows" :key="flow.label" class="cxa__flow">
            <span class="cxa__flow-icon"><component :is="flow.icon" :size="18" :stroke-width="2" /></span>
            <span class="cxa__flow-label">{{ flow.label }}</span>
            <span class="cxa__flow-bars"><i /><i /></span>
            <span class="cxa__flow-dot" />
          </div>
        </div>
        <ul class="cxa__points">
          <li v-for="point in points" :key="point"><Check :size="18" :stroke-width="2" aria-hidden="true" />{{ point }}</li>
        </ul>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { ArrowLeft, ArrowRight, Check, ShieldCheck } from 'lucide-vue-next'
import '@/features/auth/auth.css'

defineProps<{ title: string; lead?: string }>()

// Served by Frappe from the app's public folder (runtime URLs, not bundled by Vite).
const LOGO_LIGHT = '/assets/cortex_rental/images/cortex-logo.svg'
const LOGO_DARK = '/assets/cortex_rental/images/cortex-logo-reversed.svg'

// Illustration only: no data, no names, hidden from assistive technology.
const flows = [
  { label: 'Sortie', icon: ArrowRight },
  { label: 'Retour', icon: ArrowLeft },
  { label: 'Consignation', icon: ShieldCheck }
]
const points = ['Le matériel réel, jamais une copie approximative.', 'Les décisions sensibles restent entre les mains de votre équipe.', "Chaque action laisse une trace dans le journal d'audit."]

// frappe-ui switches its own tokens on `data-theme`; these screens follow the visitor's system scheme.
const media = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null
const apply = () => {
  document.documentElement.dataset.theme = media?.matches ? 'dark' : 'light'
}
onMounted(() => {
  apply()
  media?.addEventListener?.('change', apply)
})
onBeforeUnmount(() => {
  media?.removeEventListener?.('change', apply)
  delete document.documentElement.dataset.theme
})
</script>
