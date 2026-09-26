<template>
  <!-- Embed mode (?embed=1): the page alone, for the assistant's artifact panel. -->
  <main v-if="embedded" id="main-content" class="h-screen w-screen overflow-auto bg-surface-white text-ink-gray-8">
    <slot />
  </main>
  <div v-else class="flex h-screen w-screen overflow-hidden bg-surface-white text-ink-gray-8 print:block print:h-auto print:w-auto print:overflow-visible">
    <a
      href="#main-content"
      class="sr-only z-50 rounded bg-surface-white px-3 py-2 text-base text-ink-gray-9 shadow focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
    >
      {{ t('common.navigation.skip_to_content') }}
    </a>

    <AppSidebar class="hidden md:flex print:hidden" />

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0"
    >
      <div v-if="mobileMenuOpen" class="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" :aria-label="t('common.navigation.main')">
        <div class="absolute inset-0 bg-black/30" aria-hidden="true" @click="mobileMenuOpen = false" />
        <AppSidebar force-expanded class="relative h-full shadow-2xl" @navigate="mobileMenuOpen = false" />
      </div>
    </Transition>

    <div class="flex min-w-0 flex-1 flex-col print:block">
      <AppTopbar @open-menu="mobileMenuOpen = true" />
      <main id="main-content" class="flex-1 overflow-auto outline-none print:overflow-visible" tabindex="-1">
        <slot />
      </main>
    </div>

    <CopilotDrawer />
    <UniversalSearch />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppSidebar from './components/AppSidebar.vue'
import AppTopbar from './components/AppTopbar.vue'
import CopilotDrawer from './components/CopilotDrawer.vue'
import UniversalSearch from './components/UniversalSearch.vue'

const { t } = useI18n()
const route = useRoute()
const mobileMenuOpen = ref(false)
const embedded = computed(() => route.query.embed === '1')

watch(() => route.fullPath, () => (mobileMenuOpen.value = false))
</script>
