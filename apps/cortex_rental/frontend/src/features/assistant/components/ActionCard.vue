<template>
  <!-- A change the assistant proposed. Nothing happens until the person confirms. -->
  <section
    class="rounded-xl border bg-white px-4 py-3 font-sans"
    :class="proposal.status === 'proposed' ? 'border-[var(--cl-accent)]/50 shadow-[0_0_0_3px_rgba(217,119,87,0.08)]' : 'border-[var(--cl-border)]'"
    :aria-label="proposal.title"
  >
    <div class="flex items-center gap-2">
      <component :is="STATUS[proposal.status].icon" class="size-4" :class="STATUS[proposal.status].tone" :stroke-width="2" aria-hidden="true" />
      <p class="text-[12px] font-medium uppercase tracking-wide" :class="STATUS[proposal.status].tone">{{ t(`ai.action.status_${proposal.status}`) }}</p>
    </div>
    <h3 class="mt-1.5 text-[15px] font-medium text-[var(--cl-text)]">{{ proposal.title }}</h3>
    <ul v-if="proposal.impact.length" class="mt-1.5 list-disc space-y-0.5 pl-5 text-[13px] text-[#3d3d3a]">
      <li v-for="(line, index) in proposal.impact" :key="index">{{ line }}</li>
    </ul>
    <p v-if="proposal.effect" class="mt-2 text-[13px] text-[var(--cl-muted)]">{{ proposal.effect }}</p>

    <p v-if="proposal.status === 'failed' && proposal.error" class="mt-2 rounded-lg bg-surface-red-1 px-3 py-2 text-[13px] text-ink-red-4" role="alert">{{ proposal.error }}</p>
    <p v-if="error" class="mt-2 rounded-lg bg-surface-red-1 px-3 py-2 text-[13px] text-ink-red-4" role="alert">{{ error }}</p>

    <div v-if="proposal.status === 'proposed'" class="mt-3 flex items-center gap-2">
      <button
        type="button"
        class="flex items-center gap-1.5 rounded-lg bg-[var(--cl-accent)] px-3 py-1.5 text-[13px] font-medium text-white hover:bg-[var(--cl-accent-hover)] disabled:opacity-60"
        :disabled="busy !== null"
        @click="decide('confirm')"
      >
        <LoaderCircle v-if="busy === 'confirm'" class="size-3.5 animate-spin" :stroke-width="2" aria-hidden="true" />
        {{ t('ai.action.confirm') }}
      </button>
      <button
        type="button"
        class="rounded-lg px-3 py-1.5 text-[13px] text-[var(--cl-text)] hover:bg-[var(--cl-bubble)] disabled:opacity-60"
        :disabled="busy !== null"
        @click="decide('cancel')"
      >
        {{ t('ai.action.cancel') }}
      </button>
      <span class="ml-auto text-[12px] text-[var(--cl-faint)]">{{ t('ai.action.audited') }}</span>
    </div>
    <RouterLink
      v-else-if="proposal.status === 'executed' && route"
      :to="route"
      class="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[var(--cl-border)] px-3 py-1.5 text-[13px] text-[var(--cl-text)] hover:bg-[var(--cl-bubble)]"
    >
      <ArrowUpRight class="size-3.5" :stroke-width="1.75" aria-hidden="true" />{{ t('ai.action.open_result') }}
    </RouterLink>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ArrowUpRight, CircleCheck, CircleDashed, CircleSlash, CircleX, Clock, LoaderCircle } from 'lucide-vue-next'
import type { ActionProposal } from '@/api/contracts/ai'
import { useCopilotStore } from '@/stores/copilot'

const props = defineProps<{ proposal: ActionProposal }>()
const { t } = useI18n()
const copilot = useCopilotStore()
const busy = ref<'confirm' | 'cancel' | null>(null)
const error = ref('')

const STATUS = {
  proposed: { icon: CircleDashed, tone: 'text-[var(--cl-accent-hover)]' },
  executed: { icon: CircleCheck, tone: 'text-ink-green-3' },
  cancelled: { icon: CircleSlash, tone: 'text-[var(--cl-muted)]' },
  failed: { icon: CircleX, tone: 'text-ink-red-4' },
  expired: { icon: Clock, tone: 'text-[var(--cl-muted)]' }
} as const

const route = computed(() => {
  const value = props.proposal.result?.route
  return typeof value === 'string' ? value : null
})

async function decide(decision: 'confirm' | 'cancel') {
  busy.value = decision
  error.value = ''
  try {
    await copilot.decideAction(props.proposal.action_id, decision)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    busy.value = null
  }
}
</script>
