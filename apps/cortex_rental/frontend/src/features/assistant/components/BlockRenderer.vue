<template>
  <WidgetCard v-if="widget" :model="widget" :can-preview="canPreview" @open="(route, title) => $emit('open', route, title)" />
  <ActionCard v-else-if="block.type === 'action_proposal'" :proposal="block" />
  <RouterLink
    v-else-if="block.type === 'page_link'"
    :to="block.route"
    class="inline-flex items-center gap-1.5 rounded-lg border border-[var(--cl-border)] bg-white px-3 py-1.5 font-sans text-[13px] text-[var(--cl-text)] hover:bg-[var(--cl-bubble)]"
    @click.exact.prevent="$emit('open', block.route, block.label)"
  >
    <ArrowUpRight class="size-3.5 text-[var(--cl-muted)]" :stroke-width="1.75" aria-hidden="true" />{{ block.label }}
  </RouterLink>
  <ChatBlocks v-else :blocks="[block]" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ArrowUpRight } from 'lucide-vue-next'
import type { ChatBlock } from '@/api/contracts/ai'
import type { LocaleType } from '@/app/i18n'
import ChatBlocks from '@/features/copilot/components/ChatBlocks.vue'
import { widgetModel } from '../widgets'
import ActionCard from './ActionCard.vue'
import WidgetCard from './WidgetCard.vue'

const props = defineProps<{ block: ChatBlock; canPreview?: boolean }>()
defineEmits<{ open: [route: string, title: string] }>()
const { t, locale } = useI18n()

const widget = computed(() =>
  props.block.type === 'widget' ? widgetModel(props.block.tool, props.block.view, props.block.data, t, locale.value as LocaleType) : null
)
</script>
