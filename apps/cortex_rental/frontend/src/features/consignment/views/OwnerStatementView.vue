<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="statement ? t('consignment_screen.statement_title', { owner: statement.owner.display_name, period: periodLabel }) : t('routes.owner_statement')">
      <template #title-suffix>
        <StatementStatusBadge v-if="statement" :status="status" />
        <Tooltip v-if="provenance === 'mock'" :text="t('consignment_screen.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template v-if="statement" #actions>
        <Button size="sm" variant="subtle" class="print:hidden" @click="exportCsv">{{ t('finance.pnl.export_csv') }}</Button>
        <Button size="sm" variant="subtle" class="print:hidden" @click="print">{{ t('finance.pnl.print') }}</Button>
        <Button v-if="canPrepare && (status === 'not_prepared' || status === 'draft')" size="sm" :variant="status === 'not_prepared' ? 'solid' : 'subtle'" class="print:hidden" :loading="busy" @click="act('prepare')">
          {{ status === 'draft' ? t('consignment_screen.recalculate') : t('consignment_screen.prepare') }}
        </Button>
        <Button v-if="canApprove && status === 'draft'" size="sm" variant="solid" class="print:hidden" :loading="busy" @click="act('approve')">{{ t('consignment_screen.approve') }}</Button>
        <Button v-if="canApprove && status === 'approved'" size="sm" variant="solid" class="print:hidden" @click="payOpen = true">{{ t('consignment_screen.mark_paid') }}</Button>
      </template>
    </PageHeader>

    <p v-if="errorMessage" class="mx-6 mt-6 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>
    <div v-else-if="!statement" class="mx-6 mt-10 flex items-center gap-2 text-base text-ink-gray-5" role="status"><LoadingIndicator class="size-4" /> {{ t('table.loading') }}</div>

    <template v-else>
      <p class="mx-6 mt-4 rounded bg-surface-gray-1 px-3 py-2 text-p-sm text-ink-gray-6">{{ t('consignment_screen.privacy_notice') }}</p>

      <dl class="grid grid-cols-2 gap-x-8 gap-y-4 border-b border-outline-gray-1 px-6 py-5 md:grid-cols-4">
        <div><dt class="text-sm text-ink-gray-5">{{ t('consignment_screen.owner') }}</dt><dd class="mt-1 text-base">{{ statement.owner.display_name }} · {{ statement.owner.code }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('consignment_screen.period') }}</dt><dd class="mt-1 text-base">{{ date(statement.period.start) }} → {{ date(statement.period.end) }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('consignment_screen.revenue') }}</dt><dd class="mt-1 text-base tabular-nums">{{ money(statement.totals.eligible_net_revenue) }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">{{ t('consignment_screen.amount_due') }}</dt><dd class="mt-1 text-base font-semibold tabular-nums">{{ money(statement.totals.owner_amount_due) }}</dd></div>
      </dl>

      <div class="mt-4 pb-6">
        <DataTable :label="t('consignment_screen.lines')" :columns="columns" :rows="lines" row-key="key" :filter-row="false" :empty-text="t('consignment_screen.no_lines')" />
        <p class="px-6 py-3 text-p-sm text-ink-gray-5">{{ t('consignment_screen.generated', { at: dateTime(statement.generated_at), version: statement.snapshot_version }) }}</p>
      </div>
    </template>

    <ReasonDialog
      v-model="payOpen"
      :title="t('consignment_screen.mark_paid')"
      :description="t('consignment_screen.pay_description')"
      :label="t('consignment_screen.payment_reference')"
      :confirm-label="t('consignment_screen.mark_paid')"
      :cancel-label="t('common.cancel')"
      :loading="busy"
      :error="errorMessage"
      @confirm="reference => act('pay', reference)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, LoadingIndicator, Tooltip, toast } from 'frappe-ui'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import ReasonDialog from '@/design-system/components/page/ReasonDialog.vue'
import { getCortexApiClient } from '@/api'
import { OwnerStatementSafeSchema, type OwnerStatementSafe, type StatementStatus } from '@/api/contracts'
import { formatDate, formatDateTime, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'
import { downloadCsv, toCsv } from '@/utils/csv'
import StatementStatusBadge from '../components/StatementStatusBadge.vue'

const PREPARERS = ['System Manager', 'Cortex System Manager', 'Cortex Consignment Manager', 'Rental Manager']
const APPROVERS = ['System Manager', 'Cortex System Manager', 'Accounts Manager', 'Cortex Finance Manager']

const { t, locale } = useI18n()
const route = useRoute()
const session = useSessionStore()

const statement = ref<OwnerStatementSafe | null>(null)
const status = ref<StatementStatus>('not_prepared')
const provenance = ref<string | undefined>()
const errorMessage = ref('')
const busy = ref(false)
const payOpen = ref(false)

const ownerId = computed(() => String(route.params.owner))
const period = computed(() => String(route.params.period))
const canPrepare = computed(() => PREPARERS.some(role => session.hasRole(role)))
const canApprove = computed(() => APPROVERS.some(role => session.hasRole(role)))

const loc = () => locale.value as LocaleType
const money = (value: number) => formatMoney(value, statement.value?.currency, loc())
const date = (value: string) => formatDate(value, loc())
const dateTime = (value: string) => formatDateTime(value, loc())
const periodLabel = computed(() => new Intl.DateTimeFormat(locale.value, { month: 'long', year: 'numeric' }).format(new Date(`${period.value}-01T00:00:00`)))

type Line = OwnerStatementSafe['lines'][number] & Record<string, unknown> & { key: string }
const lines = computed<Line[]>(() => (statement.value?.lines ?? []).map((line, index) => ({ ...line, key: `${line.serial_number}:${index}` })))
const columns = computed<DataTableColumn<Line>[]>(() => [
  { key: 'serial_number', label: t('rental_detail.serial'), width: '170px' },
  { key: 'equipment_name', label: t('rental_detail.item'), width: '240px' },
  { key: 'rental_start_date', label: t('rentals.col_start'), width: '120px', format: row => date(row.rental_start_date) },
  { key: 'rental_end_date', label: t('rentals.col_end'), width: '120px', format: row => date(row.rental_end_date) },
  { key: 'billable_days', label: t('rentals.col_billable_days'), width: '100px', align: 'right' },
  { key: 'rate', label: t('rental_detail.daily_rate'), width: '120px', align: 'right', format: row => money(row.rate) },
  { key: 'discount_amount', label: t('rental_detail.discounts'), width: '110px', align: 'right', format: row => money(row.discount_amount) },
  { key: 'consignment_percentage', label: t('consignment_screen.share'), width: '80px', align: 'right', format: row => `${row.consignment_percentage} %` },
  { key: 'owner_amount', label: t('consignment_screen.amount_due'), width: '130px', align: 'right', format: row => money(row.owner_amount) }
])

async function load() {
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().getOwnerStatement({ owner_id: ownerId.value, period: period.value })
    // Privacy guard: display only what matches the strict owner-safe contract.
    const parsed = OwnerStatementSafeSchema.safeParse(result.statement)
    if (!parsed.success) throw new Error(t('consignment_screen.privacy_refused'))
    statement.value = parsed.data
    status.value = result.status ?? 'not_prepared'
    provenance.value = result.provenance
  } catch (error) {
    statement.value = null
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

async function act(action: 'prepare' | 'approve' | 'pay', reference?: string) {
  busy.value = true
  errorMessage.value = ''
  try {
    const api = getCortexApiClient()
    if (action === 'prepare') await api.prepareStatement(ownerId.value, period.value)
    if (action === 'approve') await api.approveStatement(ownerId.value, period.value)
    if (action === 'pay') await api.markStatementPaid(ownerId.value, period.value, reference ?? '')
    toast.create({ message: t(`consignment_screen.done_${action}`), type: 'success' })
    payOpen.value = false
    await load()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    busy.value = false
  }
}

function exportCsv() {
  const s = statement.value!
  const rows: Array<Array<string | number>> = [
    [t('rental_detail.serial'), t('rental_detail.item'), t('rentals.col_start'), t('rentals.col_end'), t('rentals.col_billable_days'), t('rental_detail.daily_rate'), t('rental_detail.discounts'), t('consignment_screen.share'), t('consignment_screen.amount_due')],
    ...s.lines.map(line => [line.serial_number, line.equipment_name, line.rental_start_date, line.rental_end_date, line.billable_days, line.rate, line.discount_amount, line.consignment_percentage, line.owner_amount]),
    ['', '', '', '', '', '', '', t('consignment_screen.amount_due'), s.totals.owner_amount_due]
  ]
  downloadCsv(`releve-${s.owner.code}-${period.value}.csv`, toCsv(rows))
}

function print() {
  window.print()
}

watch(() => route.fullPath, () => void load())
onMounted(load)
</script>
