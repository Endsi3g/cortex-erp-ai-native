<template>
  <!--
    Renders the server's typed blocks (schemas/chat_schemas.py). Verified
    facts and model text never share the same visual weight: model text is
    plain, facts carry their source and check time, extracted values carry
    the model's own confidence label.
  -->
  <div class="space-y-2">
    <template v-for="(block, index) in blocks" :key="index">
      <p v-if="block.type === 'assistant_text'" class="whitespace-pre-wrap text-p-base text-ink-gray-8">{{ block.text }}</p>

      <div v-else-if="block.type === 'verified_fact'" class="rounded border border-outline-gray-2 bg-surface-white p-3">
        <div class="flex items-center gap-1.5 text-sm font-medium text-ink-gray-9">
          <ShieldCheck class="size-4 text-ink-green-3" :stroke-width="1.5" aria-hidden="true" />
          {{ block.title }}
        </div>
        <ul class="mt-1.5 list-disc space-y-0.5 pl-5 text-p-sm text-ink-gray-7">
          <li v-for="(item, i) in block.items" :key="i">{{ item }}</li>
        </ul>
        <p class="mt-1.5 text-xs text-ink-gray-5">{{ t('ai.checked_at', { at: formatDateTimeLocal(block.checked_at) }) }}<template v-if="block.source_ids.length"> · {{ block.source_ids.join(', ') }}</template></p>
      </div>

      <div v-else-if="block.type === 'extracted_data'" class="rounded border border-outline-gray-2 bg-surface-white">
        <div class="border-b border-outline-gray-1 px-3 py-2 text-sm font-medium text-ink-gray-9">{{ block.title }}</div>
        <dl class="divide-y divide-outline-gray-1">
          <div v-for="(field, i) in block.fields" :key="i" class="grid grid-cols-[120px_1fr_auto] items-center gap-2 px-3 py-1.5 text-p-sm">
            <dt class="text-ink-gray-5">{{ field.label }}</dt>
            <dd class="text-ink-gray-8">{{ field.value }}</dd>
            <Badge :theme="field.confidence === 'high' ? 'green' : field.confidence === 'medium' ? 'orange' : 'red'" variant="subtle" size="sm">{{ t(`ai.level_${field.confidence}`) }}</Badge>
          </div>
        </dl>
      </div>

      <div v-else-if="block.type === 'proposal'" class="rounded border border-outline-gray-2 bg-surface-gray-1 p-3">
        <div class="text-sm font-medium text-ink-gray-9">{{ block.title }}</div>
        <p class="mt-1 text-p-sm text-ink-gray-7">{{ block.summary }}</p>
        <ul v-if="block.impact.length" class="mt-1.5 list-disc space-y-0.5 pl-5 text-p-sm text-ink-gray-7">
          <li v-for="(item, i) in block.impact" :key="i">{{ item }}</li>
        </ul>
        <div class="mt-2 flex items-center gap-2">
          <Button v-if="block.draft_id" size="sm" variant="subtle" @click="router.push({ name: 'rental-detail', params: { name: block.draft_id } })">{{ t('ai.open_draft', { name: block.draft_id }) }}</Button>
          <Button v-else size="sm" variant="subtle" @click="router.push({ name: 'rental-composer' })">{{ t('ai.open_composer') }}</Button>
          <span v-if="block.requires_approval" class="text-xs text-ink-gray-5">{{ t('ai.requires_approval') }}</span>
        </div>
      </div>

      <div v-else-if="block.type === 'approval_required'" class="rounded border border-outline-amber-2 bg-surface-amber-1 p-3">
        <div class="text-sm font-medium text-ink-gray-9">{{ block.action_label }}</div>
        <ul class="mt-1.5 space-y-0.5 text-p-sm">
          <li v-for="(req, i) in block.requirements" :key="i" class="flex items-center gap-1.5" :class="req.passed ? 'text-ink-gray-7' : 'text-ink-red-4'">
            <component :is="req.passed ? Check : X" class="size-3.5" :stroke-width="2" aria-hidden="true" />
            {{ req.label }}
          </li>
        </ul>
        <Button class="mt-2" size="sm" variant="subtle" @click="router.push({ name: 'ai-workspace', params: { itemId: `approval:${block.approval_request_id}` } })">{{ t('ai.open_approval') }}</Button>
      </div>

      <div
        v-else-if="block.type === 'risk'"
        class="rounded border p-3"
        :class="block.severity === 'danger' ? 'border-outline-red-1 bg-surface-red-1' : block.severity === 'warning' ? 'border-outline-amber-2 bg-surface-amber-1' : 'border-outline-gray-2 bg-surface-gray-1'"
        role="note"
      >
        <div class="flex items-center gap-1.5 text-sm font-medium text-ink-gray-9">
          <TriangleAlert class="size-4" :stroke-width="1.5" aria-hidden="true" />
          {{ block.title }}
        </div>
        <p class="mt-1 text-p-sm text-ink-gray-7">{{ block.explanation }}</p>
      </div>

      <div v-else-if="block.type === 'missing_information'" class="rounded border border-outline-gray-2 bg-surface-gray-1 p-3 text-p-sm">
        <div class="font-medium text-ink-gray-9">{{ t('ai.missing_information') }}</div>
        <p class="mt-1 text-ink-gray-7">{{ block.fields.join(', ') }}</p>
        <p v-if="block.suggested_next_action" class="mt-1 text-ink-gray-5">{{ block.suggested_next_action }}</p>
      </div>

      <p v-else-if="block.type === 'tool_progress'" class="flex items-center gap-1.5 text-xs text-ink-gray-5">
        <Wrench class="size-3.5" :stroke-width="1.5" aria-hidden="true" />
        <span class="font-mono">{{ block.tool_name }}</span> · {{ block.message }}
      </p>

      <div v-else-if="block.type === 'error'" class="rounded border border-outline-red-1 bg-surface-red-1 p-3 text-p-sm" role="alert">
        <div class="font-medium text-ink-red-4">{{ block.title }}</div>
        <p class="mt-1 text-ink-gray-7">{{ block.safe_message }}</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Badge, Button } from 'frappe-ui'
import { Check, ShieldCheck, TriangleAlert, Wrench, X } from 'lucide-vue-next'
import type { ChatBlock } from '@/api/contracts/ai'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

defineProps<{ blocks: ChatBlock[] }>()

const { t, locale } = useI18n()
const router = useRouter()

function formatDateTimeLocal(value: string) {
  return formatDateTime(value, locale.value as LocaleType)
}
</script>
