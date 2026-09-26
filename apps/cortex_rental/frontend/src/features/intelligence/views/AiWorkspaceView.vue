<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="title">
      <template #title-suffix>
        <Badge v-if="rowState" :theme="INBOX_STATE_THEME[rowState]" variant="subtle" size="md">{{ t(`ai.state_${rowState}`) }}</Badge>
        <Tooltip v-if="demo" :text="t('ai.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" @click="router.push({ name: 'ai-inbox' })">{{ t('ai.back_to_inbox') }}</Button>
      </template>
    </PageHeader>

    <p v-if="!parsed" class="px-6 py-10 text-center text-p-base text-ink-gray-5">{{ t('ai.pick_item') }}</p>
    <p v-else-if="loading" class="px-6 py-10 text-center text-p-base text-ink-gray-5" role="status">{{ t('table.loading') }}</p>
    <p v-else-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div v-else-if="detail" class="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
      <!-- Left: the source, as received / as stored -->
      <section class="border-b border-outline-gray-1 px-6 py-5 lg:border-b-0 lg:border-r" :aria-label="t('ai.source')">
        <h2 class="mb-4 text-base font-semibold text-ink-gray-9">{{ t('ai.source') }}</h2>

        <template v-if="detail.kind === 'inbound'">
          <dl class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-base">
            <dt class="text-ink-gray-5">{{ t('ai.sender') }}</dt><dd class="text-ink-gray-8">{{ detail.sender_email || '—' }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.channel') }}</dt><dd class="text-ink-gray-8">{{ detail.source_channel }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.received') }}</dt><dd class="text-ink-gray-8">{{ fmt(detail.received_at) }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.status') }}</dt><dd class="text-ink-gray-8">{{ t(`ai.inbound_${detail.status}`) }}</dd>
          </dl>
          <pre class="mt-4 max-h-[420px] overflow-auto whitespace-pre-wrap rounded border border-outline-gray-1 bg-surface-gray-1 p-3 font-sans text-p-base text-ink-gray-8">{{ detail.raw_text || t('ai.no_text') }}</pre>
          <h3 class="mb-2 mt-5 text-sm font-medium text-ink-gray-7">{{ t('ai.evidence') }}</h3>
          <p v-if="!detail.evidence.length" class="text-p-sm text-ink-gray-5">{{ t('ai.no_evidence') }}</p>
          <ul v-else class="divide-y divide-outline-gray-1 rounded border border-outline-gray-1">
            <li v-for="item in detail.evidence" :key="item.id" class="px-3 py-2 text-p-sm">
              <div class="flex items-center justify-between gap-2">
                <span class="font-mono text-ink-gray-8">{{ item.id }}</span>
                <span class="text-ink-gray-5">{{ item.mime_type || item.channel }} · {{ item.scanned_clean ? t('ai.scanned_clean') : t('ai.not_scanned') }}</span>
              </div>
              <p v-if="item.excerpt" class="mt-1 text-ink-gray-6">{{ item.excerpt }}</p>
            </li>
          </ul>
        </template>

        <template v-else-if="detail.kind === 'approval'">
          <dl class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-base">
            <dt class="text-ink-gray-5">{{ t('ai.entity') }}</dt>
            <dd>
              <RouterLink v-if="detail.entity_type === 'Cortex Rental Transaction'" class="text-ink-gray-9 underline" :to="{ name: 'rental-detail', params: { name: detail.entity_id } }">{{ detail.entity_id }}</RouterLink>
              <span v-else class="text-ink-gray-8">{{ detail.entity_type }} {{ detail.entity_id }}</span>
            </dd>
            <dt class="text-ink-gray-5">{{ t('ai.requested_by') }}</dt><dd class="text-ink-gray-8">{{ detail.row.requested_by }} · {{ t(`ai.requester_${detail.row.requested_by_type}`) }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.received') }}</dt><dd class="text-ink-gray-8">{{ fmt(detail.row.created_at) }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.status') }}</dt><dd class="text-ink-gray-8">{{ t(`ai.approval_${detail.status}`) }}</dd>
          </dl>
          <p v-if="detail.row.summary" class="mt-4 rounded border border-outline-gray-1 bg-surface-gray-1 p-3 text-p-base text-ink-gray-8">{{ detail.row.summary }}</p>
          <h3 class="mb-2 mt-5 text-sm font-medium text-ink-gray-7">{{ t('ai.change') }}</h3>
          <table class="w-full border-collapse border-t border-outline-gray-1 text-base">
            <thead>
              <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
                <th class="border-r border-outline-gray-1 px-2 text-left font-normal">{{ t('ai.field') }}</th>
                <th class="border-r border-outline-gray-1 px-2 text-left font-normal">{{ t('ai.current') }}</th>
                <th class="px-2 text-left font-normal">{{ t('ai.proposed') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="key in changeKeys" :key="key" class="h-[33px] border-b border-outline-gray-1">
                <td class="border-r border-outline-gray-1 px-2 text-ink-gray-6">{{ key }}</td>
                <td class="border-r border-outline-gray-1 px-2 text-ink-gray-8">{{ show(detail.current[key]) }}</td>
                <td class="px-2 text-ink-gray-9" :class="show(detail.current[key]) !== show(detail.proposed[key]) ? 'font-medium' : ''">{{ show(detail.proposed[key]) }}</td>
              </tr>
              <tr v-if="!changeKeys.length" class="h-[33px]"><td colspan="3" class="px-2 text-ink-gray-5">{{ t('ai.no_change_payload') }}</td></tr>
            </tbody>
          </table>
        </template>

        <template v-else-if="detail.kind === 'draft'">
          <dl class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-base">
            <dt class="text-ink-gray-5">{{ t('ai.customer') }}</dt><dd class="text-ink-gray-8">{{ detail.rental.customer_name }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.period') }}</dt><dd class="text-ink-gray-8">{{ fmt(detail.rental.starts_at) }} → {{ fmt(detail.rental.ends_at) }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.status') }}</dt><dd class="text-ink-gray-8">{{ t(`rental_states.${detail.rental.rental_state}`) }}</dd>
          </dl>
          <table class="mt-4 w-full border-collapse border-t border-outline-gray-1 text-base">
            <thead>
              <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
                <th class="border-r border-outline-gray-1 px-2 text-left font-normal">{{ t('ai.item') }}</th>
                <th class="border-r border-outline-gray-1 px-2 text-right font-normal">{{ t('ai.quantity') }}</th>
                <th class="px-2 text-right font-normal">{{ t('ai.amount') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(line, index) in detail.rental.items" :key="index" class="h-[33px] border-b border-outline-gray-1">
                <td class="border-r border-outline-gray-1 px-2 text-ink-gray-8">{{ line.item_name || line.item_code }}</td>
                <td class="border-r border-outline-gray-1 px-2 text-right text-ink-gray-8">{{ line.quantity }}</td>
                <td class="px-2 text-right text-ink-gray-8">{{ money(line.subtotal) }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </section>

      <!-- Right: what the AI did, and what a person can decide -->
      <section class="px-6 py-5" :aria-label="t('ai.ai_work')">
        <h2 class="mb-4 text-base font-semibold text-ink-gray-9">{{ t('ai.ai_work') }}</h2>

        <template v-if="detail.kind === 'inbound'">
          <p v-if="!detail.extraction" class="text-p-base text-ink-gray-5">{{ t('ai.no_extraction') }}</p>
          <template v-else>
            <dl class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-base">
              <dt class="text-ink-gray-5">{{ t('ai.agent') }}</dt><dd class="text-ink-gray-8">{{ detail.extraction.agent }}<template v-if="detail.extraction.model"> · {{ detail.extraction.model }}</template></dd>
              <dt class="text-ink-gray-5">{{ t('ai.extracted_at') }}</dt><dd class="text-ink-gray-8">{{ fmt(detail.extraction.extracted_at) }}</dd>
              <dt class="text-ink-gray-5">{{ t('ai.validation') }}</dt>
              <dd><Badge :theme="detail.extraction.validation_status === 'Valid' ? 'green' : 'red'" variant="subtle">{{ t(`ai.validation_${detail.extraction.validation_status}`) }}</Badge></dd>
              <dt class="text-ink-gray-5">{{ t('ai.model_score') }}</dt>
              <dd class="text-ink-gray-8">{{ formatScore(detail.extraction.overall_confidence) }} <span class="text-ink-gray-5">· {{ t('ai.not_calibrated') }}</span></dd>
            </dl>

            <ul v-if="detail.extraction.validation_errors.length" class="mt-4 list-disc space-y-0.5 rounded border border-outline-red-1 bg-surface-red-1 py-2 pl-7 pr-3 text-p-sm text-ink-red-4" role="alert">
              <li v-for="(error, index) in detail.extraction.validation_errors" :key="index">{{ error }}</li>
            </ul>

            <h3 class="mb-2 mt-5 text-sm font-medium text-ink-gray-7">{{ t('ai.extracted_fields') }}</h3>
            <table class="w-full border-collapse border-t border-outline-gray-1 text-base">
              <tbody>
                <tr v-for="field in extractedFields" :key="field.key" class="h-[33px] border-b border-outline-gray-1">
                  <td class="w-[140px] border-r border-outline-gray-1 px-2 text-ink-gray-6">{{ field.label }}</td>
                  <td class="border-r border-outline-gray-1 px-2" :class="field.value ? 'text-ink-gray-8' : 'text-ink-red-4'">{{ field.value || t('ai.missing') }}</td>
                  <td class="w-[80px] px-2 text-right text-ink-gray-6">{{ formatScore(field.score) }}</td>
                </tr>
              </tbody>
            </table>

            <h3 class="mb-2 mt-5 text-sm font-medium text-ink-gray-7">{{ t('ai.requested_items') }}</h3>
            <table class="w-full border-collapse border-t border-outline-gray-1 text-base">
              <thead>
                <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
                  <th class="border-r border-outline-gray-1 px-2 text-left font-normal">{{ t('ai.as_written') }}</th>
                  <th class="border-r border-outline-gray-1 px-2 text-right font-normal">{{ t('ai.quantity') }}</th>
                  <th class="border-r border-outline-gray-1 px-2 text-left font-normal">{{ t('ai.matched_item') }}</th>
                  <th class="px-2 text-right font-normal">{{ t('ai.model_score') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in detail.extraction.payload.items ?? []" :key="index" class="h-[33px] border-b border-outline-gray-1">
                  <td class="border-r border-outline-gray-1 px-2 text-ink-gray-8">{{ item.raw_text }}</td>
                  <td class="border-r border-outline-gray-1 px-2 text-right text-ink-gray-8">{{ item.quantity }}</td>
                  <td class="border-r border-outline-gray-1 px-2" :class="item.matched_item_code ? 'font-mono text-ink-gray-8' : 'text-ink-red-4'">{{ item.matched_item_code || t('ai.no_match') }}</td>
                  <td class="px-2 text-right text-ink-gray-6">{{ formatScore(item.confidence) }}</td>
                </tr>
                <tr v-if="!(detail.extraction.payload.items ?? []).length" class="h-[33px]"><td colspan="4" class="px-2 text-ink-gray-5">{{ t('ai.no_items') }}</td></tr>
              </tbody>
            </table>
            <p v-if="detail.extraction.missing_fields.length" class="mt-4 rounded border border-outline-amber-2 bg-surface-amber-1 px-3 py-2 text-p-sm text-ink-gray-8">{{ t('ai.to_complete', { fields: detail.extraction.missing_fields.join(', ') }) }}</p>
          </template>

          <div class="mt-6 border-t border-outline-gray-1 pt-4">
            <p v-if="detail.extracted_transaction" class="text-p-base text-ink-gray-8">
              {{ t('ai.linked_to') }}
              <RouterLink class="underline" :to="{ name: 'rental-detail', params: { name: detail.extracted_transaction } }">{{ detail.extracted_transaction }}</RouterLink>
            </p>
            <template v-else-if="inboundOpen">
              <div class="flex flex-wrap gap-2">
                <Button variant="solid" size="sm" @click="prepareRental">{{ t('ai.prepare_rental') }}</Button>
                <Button variant="subtle" size="sm" theme="red" @click="rejectOpen = true">{{ t('ai.reject_request') }}</Button>
              </div>
              <p class="mt-2 text-p-sm text-ink-gray-5">{{ t('ai.prepare_rental_effect') }}</p>
            </template>
          </div>
        </template>

        <template v-else-if="detail.kind === 'approval'">
          <dl class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-base">
            <dt class="text-ink-gray-5">{{ t('ai.agent') }}</dt><dd class="text-ink-gray-8">{{ detail.row.agent ?? '—' }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.evidence') }}</dt><dd class="font-mono text-ink-gray-8">{{ detail.evidence_ids.join(', ') || '—' }}</dd>
          </dl>
          <h3 class="mb-2 mt-5 text-sm font-medium text-ink-gray-7">{{ t('ai.policy_decision') }}</h3>
          <dl v-if="Object.keys(detail.policy_decision).length" class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-1 text-p-sm">
            <template v-for="(value, key) in detail.policy_decision" :key="key">
              <dt class="text-ink-gray-5">{{ key }}</dt><dd class="text-ink-gray-8">{{ show(value) }}</dd>
            </template>
          </dl>
          <p v-else class="text-p-sm text-ink-gray-5">—</p>

          <div class="mt-6 border-t border-outline-gray-1 pt-4">
            <template v-if="detail.status === 'Pending'">
              <p v-if="!canDecide" class="text-p-sm text-ink-gray-5">{{ t('ai.cannot_decide') }}</p>
              <p v-else-if="detail.self_requested" class="text-p-sm text-ink-gray-5">{{ t('ai.self_requested') }}</p>
              <template v-else>
                <div class="flex flex-wrap gap-2">
                  <Button variant="solid" size="sm" :loading="deciding" @click="approve">{{ t('ai.approve') }}</Button>
                  <Button variant="subtle" size="sm" theme="red" :disabled="deciding" @click="rejectOpen = true">{{ t('ai.reject') }}</Button>
                </div>
                <p class="mt-2 text-p-sm text-ink-gray-5">{{ approveEffect }}</p>
              </template>
            </template>
            <p v-else class="text-p-base text-ink-gray-8">{{ t('ai.decided', { status: t(`ai.approval_${detail.status}`), by: detail.decided_by ?? '—', at: detail.decided_at ? fmt(detail.decided_at) : '—' }) }}<template v-if="detail.decision_reason"> — {{ detail.decision_reason }}</template></p>
          </div>
        </template>

        <template v-else-if="detail.kind === 'draft'">
          <dl class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-base">
            <dt class="text-ink-gray-5">{{ t('ai.agent') }}</dt><dd class="text-ink-gray-8">{{ row?.agent ?? '—' }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.created') }}</dt><dd class="text-ink-gray-8">{{ row ? fmt(row.created_at) : '—' }}</dd>
            <dt class="text-ink-gray-5">{{ t('ai.pricing') }}</dt><dd class="text-ink-gray-8">{{ t('ai.server_priced') }}</dd>
          </dl>
          <div class="mt-6 border-t border-outline-gray-1 pt-4">
            <Button variant="solid" size="sm" @click="router.push({ name: 'rental-detail', params: { name: detail.rental.id } })">{{ t('ai.review_rental') }}</Button>
            <p class="mt-2 text-p-sm text-ink-gray-5">{{ t('ai.review_rental_effect') }}</p>
          </div>
        </template>
      </section>
    </div>

    <ReasonDialog
      v-model="rejectOpen"
      :title="detail?.kind === 'approval' ? t('ai.reject') : t('ai.reject_request')"
      :label="t('ai.reason')"
      :description="detail?.kind === 'approval' ? t('ai.reject_approval_effect') : t('ai.reject_request_effect')"
      :confirm-label="t('ai.reject')"
      :cancel-label="t('common.cancel')"
      danger
      :loading="deciding"
      :error="decisionError"
      @confirm="reject"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Tooltip, toast } from 'frappe-ui'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import ReasonDialog from '@/design-system/components/page/ReasonDialog.vue'
import { MockCortexApiClient, getCortexApiClient } from '@/api'
import type { InboxDetail, InboxItem, InboxKind, InboxState } from '@/api/contracts/ai'
import { formatDateTime, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'
import { useApprovalsStore } from '@/stores/approvals'
import { INBOX_STATE_THEME, formatScore } from '../inboxStates'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const approvals = useApprovalsStore()

const detail = ref<InboxDetail | null>(null)
const row = ref<InboxItem | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const rejectOpen = ref(false)
const deciding = ref(false)
const decisionError = ref('')
const demo = getCortexApiClient() instanceof MockCortexApiClient

const parsed = computed(() => {
  const raw = typeof route.params.itemId === 'string' ? route.params.itemId : ''
  const index = raw.indexOf(':')
  if (index < 1) return null
  const kind = raw.slice(0, index) as InboxKind
  return ['approval', 'inbound', 'draft'].includes(kind) ? { kind, sourceId: raw.slice(index + 1) } : null
})

const canDecide = computed(() => session.hasPermission('cortex:approvals:decide'))
const fmt = (value: string) => formatDateTime(value, locale.value as LocaleType)
const money = (value: number) => formatMoney(value, detail.value?.kind === 'draft' ? detail.value.rental.currency : null, locale.value as LocaleType)
const show = (value: unknown) => (value === null || value === undefined || value === '' ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value))

const title = computed(() => {
  if (!detail.value) return t('routes.ai_workspace')
  if (detail.value.kind === 'inbound') return detail.value.subject || detail.value.id
  if (detail.value.kind === 'approval') return detail.value.row.title
  return detail.value.rental.id
})

const rowState = computed<InboxState | null>(() => (detail.value?.kind === 'approval' ? detail.value.row.state : row.value?.state ?? null))
const inboundOpen = computed(() => detail.value?.kind === 'inbound' && !['Rejected', 'Processed'].includes(detail.value.status))

const changeKeys = computed(() => {
  if (detail.value?.kind !== 'approval') return []
  return [...new Set([...Object.keys(detail.value.proposed), ...Object.keys(detail.value.current)])]
})

const extractedFields = computed(() => {
  if (detail.value?.kind !== 'inbound' || !detail.value.extraction) return []
  const { customer = {}, rental_period: period = {} } = detail.value.extraction.payload
  return [
    { key: 'company', label: t('ai.field_company'), value: customer.company_name ?? '', score: customer.confidence },
    { key: 'contact', label: t('ai.field_contact'), value: customer.name ?? '', score: customer.confidence },
    { key: 'email', label: t('ai.field_email'), value: customer.email ?? '', score: customer.confidence },
    { key: 'start', label: t('ai.field_start'), value: period.starts_at ? fmt(period.starts_at) : '', score: period.confidence },
    { key: 'end', label: t('ai.field_end'), value: period.ends_at ? fmt(period.ends_at) : '', score: period.confidence }
  ]
})

const approveEffect = computed(() => {
  if (detail.value?.kind !== 'approval') return ''
  const target = detail.value.proposed.rental_state
  return target
    ? t('ai.approve_effect_transition', { entity: detail.value.entity_id, state: t(`rental_states.${String(target)}`) })
    : t('ai.approve_effect', { entity: `${detail.value.entity_type} ${detail.value.entity_id}` })
})

async function load() {
  detail.value = null
  row.value = null
  errorMessage.value = ''
  if (!parsed.value) return
  loading.value = true
  try {
    const api = getCortexApiClient()
    const [item, list] = await Promise.all([
      api.getInboxItem(parsed.value.kind, parsed.value.sourceId),
      api.listInbox(parsed.value.kind, true).catch(() => null)
    ])
    detail.value = item
    row.value = list?.items.find(entry => entry.source_id === parsed.value?.sourceId) ?? null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function prepareRental() {
  if (detail.value?.kind !== 'inbound') return
  const payload = detail.value.extraction?.payload
  const codes = (payload?.items ?? []).map(item => item.matched_item_code).filter((code): code is string => Boolean(code))
  void router.push({
    name: 'rental-composer',
    query: {
      inbound: detail.value.id,
      items: codes.length ? codes.join(',') : undefined,
      starts_at: payload?.rental_period?.starts_at,
      ends_at: payload?.rental_period?.ends_at
    }
  })
}

async function approve() {
  if (detail.value?.kind !== 'approval') return
  deciding.value = true
  try {
    await getCortexApiClient().approveApprovalRequest({ id: detail.value.row.source_id, notes: undefined })
    toast.create({ message: t('ai.approved'), type: 'success' })
    void approvals.fetchPendingApprovals()
    await load()
  } catch (error) {
    toast.create({ message: error instanceof Error ? error.message : String(error), type: 'error' })
  } finally {
    deciding.value = false
  }
}

async function reject(reason: string) {
  if (!detail.value) return
  deciding.value = true
  decisionError.value = ''
  try {
    const api = getCortexApiClient()
    if (detail.value.kind === 'approval') {
      await api.rejectApprovalRequest({ id: detail.value.row.source_id, reason })
      void approvals.fetchPendingApprovals()
    } else if (detail.value.kind === 'inbound') {
      await api.rejectInbound(detail.value.id, reason)
    }
    rejectOpen.value = false
    toast.create({ message: t('ai.rejected'), type: 'success' })
    await load()
  } catch (error) {
    decisionError.value = error instanceof Error ? error.message : String(error)
  } finally {
    deciding.value = false
  }
}

watch(() => route.params.itemId, () => void load(), { immediate: true })
</script>
