<template>
  <div class="inline-flex items-center rounded-lg border border-cortex-border bg-cortex-surface p-0.5 shadow-sm">
    <button
      type="button"
      @click="setLanguage('fr-CA')"
      class="px-2 py-1 text-xs font-semibold rounded-md transition-colors focus:outline-none"
      :class="[
        sessionStore.locale === 'fr-CA'
          ? 'bg-cortex-primary-600 text-white shadow-xs'
          : 'text-cortex-text-muted hover:text-cortex-text-primary'
      ]"
      title="Français (Canada)"
      aria-label="Passer en Français"
    >
      FR
    </button>

    <button
      type="button"
      @click="setLanguage('en-CA')"
      class="px-2 py-1 text-xs font-semibold rounded-md transition-colors focus:outline-none"
      :class="[
        sessionStore.locale === 'en-CA'
          ? 'bg-cortex-primary-600 text-white shadow-xs'
          : 'text-cortex-text-muted hover:text-cortex-text-primary'
      ]"
      title="English (Canada)"
      aria-label="Switch to English"
    >
      EN
    </button>
  </div>
</template>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import type { LocaleType } from '@/app/i18n'

const sessionStore = useSessionStore()

const setLanguage = (locale: LocaleType) => {
  sessionStore.setLocale(locale)
}
</script>
