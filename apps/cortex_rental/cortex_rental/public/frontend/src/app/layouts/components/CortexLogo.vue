<template>
  <RouterLink
    to="/app/cortex-operations"
    class="flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors hover:bg-cortex-surface-subtle group focus:outline-none focus:ring-2 focus:ring-cortex-primary-500"
    :title="t('common.actions.back_to_overview')"
    aria-label="Cortex — Retour au cockpit d'opérations"
  >
    <!-- "Return ring" symbol, small-size cut (docs/brand/logo-kit). The dot is the only accent. -->
    <svg
      viewBox="20 20 216 216"
      class="w-8 h-8 flex-shrink-0"
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        class="fill-current text-cortex-ink-900"
        d="M205.37 51.63A108 108 0 1 0 205.37 204.37L164.36 163.36A50 50 0 1 1 164.36 92.64Z"
      />
      <circle class="fill-current text-cortex-primary-600" cx="208" cy="128" r="27" />
    </svg>

    <!-- Wordmark: Inter SemiBold, same face as the logo files -->
    <span
      v-if="!collapsed"
      class="text-lg font-semibold tracking-tight text-cortex-ink-900 font-sans leading-none"
    >
      Cortex
    </span>
  </RouterLink>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

withDefaults(
  defineProps<{
    collapsed?: boolean
  }>(),
  {
    collapsed: false
  }
)

const { t } = useI18n()
</script>
