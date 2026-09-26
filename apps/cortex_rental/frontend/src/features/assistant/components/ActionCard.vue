<template>
  <!-- A change the assistant proposed. Confirmation is wired in phase D. -->
  <section class="rounded-xl border border-[var(--cl-border-strong)] bg-white px-4 py-3 font-sans" :aria-label="proposal.title">
    <p class="text-[12px] font-medium uppercase tracking-wide text-[var(--cl-accent-hover)]">{{ t('ai.action.proposed') }}</p>
    <h3 class="mt-1 text-[15px] font-medium text-[var(--cl-text)]">{{ proposal.title }}</h3>
    <ul v-if="proposal.impact.length" class="mt-1.5 list-disc space-y-0.5 pl-5 text-[13px] text-[#3d3d3a]">
      <li v-for="(line, index) in proposal.impact" :key="index">{{ line }}</li>
    </ul>
    <p v-if="proposal.effect" class="mt-2 text-[13px] text-[var(--cl-muted)]">{{ proposal.effect }}</p>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { ActionProposal } from '@/api/contracts/ai'

defineProps<{ proposal: ActionProposal }>()
const { t } = useI18n()
</script>
