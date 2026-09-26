<template>
  <div class="space-y-5">
    <div v-if="loading && !billing" class="flex items-center gap-2 text-base text-ink-gray-5" role="status">
      <LoadingIndicator class="size-4" /> {{ t('rental_detail.billing.loading') }}
    </div>
    <div v-else-if="errorMessage && !billing" class="rounded border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-p-sm text-ink-red-4" role="alert">
      {{ errorMessage }}
    </div>

    <template v-else-if="billing">
      <p v-if="!billing.sales_order" class="rounded border border-outline-gray-1 bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-6">
        {{ t('rental_detail.billing.no_order') }}
      </p>

      <template v-else>
        <dl class="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt class="text-sm text-ink-gray-5">{{ t('rental_detail.billing.sales_order') }}</dt>
            <dd class="mt-1 text-base">
              <a :href="deskUrl('sales-order', billing.sales_order.name)" target="_blank" rel="noopener" class="text-ink-gray-8 underline decoration-outline-gray-3 underline-offset-2">{{ billing.sales_order.name }}</a>
              <span class="ml-2 text-sm text-ink-gray-5">{{ billing.sales_order.status }}</span>
            </dd>
          </div>
          <div>
            <dt class="text-sm text-ink-gray-5">{{ t('rental_detail.billing.order_total') }}</dt>
            <dd class="mt-1 text-base tabular-nums">{{ money(billing.sales_order.grand_total) }}</dd>
          </div>
          <div>
            <dt class="text-sm text-ink-gray-5">{{ t('rental_detail.billing.advance_requested') }}</dt>
            <dd class="mt-1 text-base tabular-nums">{{ money(billing.advance.requested) }}</dd>
            <dd class="text-sm text-ink-gray-5">
              {{ t('rental_detail.billing.advance_split', { share: money(billing.advance.percentage_amount), guarantee: money(billing.advance.guarantee_amount) }) }}
            </dd>
          </div>
          <div>
            <dt class="text-sm text-ink-gray-5">{{ t('rental_detail.billing.advance_received') }}</dt>
            <dd class="mt-1 flex items-center gap-2 text-base tabular-nums">
              {{ money(billing.advance.received) }}
              <Badge :theme="billing.advance.covered ? 'green' : 'orange'" variant="subtle">
                {{ billing.advance.covered ? t('rental_detail.billing.covered') : t('rental_detail.billing.not_covered') }}
              </Badge>
            </dd>
          </div>
        </dl>

        <div class="flex flex-wrap gap-2">
          <Button v-if="canRecordAdvance" size="sm" variant="subtle" @click="openAdvance">{{ t('rental_detail.billing.record_advance') }}</Button>
          <Button v-if="canPrepareInvoice" size="sm" variant="solid" :loading="preparing" @click="prepareInvoice">{{ t('rental_detail.billing.prepare_invoice') }}</Button>
        </div>

        <section>
          <h3 class="mb-2 text-base font-semibold text-ink-gray-9">{{ t('rental_detail.billing.payments') }}</h3>
          <DataTable
            :label="t('rental_detail.billing.payments')"
            :columns="paymentColumns"
            :rows="billing.payments"
            :filter-row="false"
            :empty-text="t('rental_detail.billing.no_payments')"
            clickable
            @row-click="row => openDesk('payment-entry', String(row.name))"
          >
            <template #cell-docstatus="{ row }">
              <Badge :theme="row.docstatus === 1 ? 'green' : 'gray'" variant="subtle">
                {{ row.docstatus === 1 ? t('finance.invoices.payment_submitted') : t('finance.invoices.payment_draft') }}
              </Badge>
            </template>
          </DataTable>
        </section>

        <section v-if="billing.final_invoice" class="rounded border border-outline-gray-1 px-4 py-3">
          <h3 class="text-base font-semibold text-ink-gray-9">{{ t('rental_detail.billing.final_invoice') }}</h3>
          <p class="mt-1 text-base">
            <a :href="deskUrl('sales-invoice', billing.final_invoice.name)" target="_blank" rel="noopener" class="underline decoration-outline-gray-3 underline-offset-2">{{ billing.final_invoice.name }}</a>
            · {{ billing.final_invoice.docstatus === 0 ? t('rental_detail.billing.invoice_draft') : billing.final_invoice.status }}
            · {{ t('rental_detail.billing.invoice_amounts', { total: money(billing.final_invoice.grand_total), advance: money(billing.final_invoice.total_advance), due: money(billing.final_invoice.outstanding_amount) }) }}
          </p>
          <p v-if="billing.final_invoice.docstatus === 0" class="mt-1 text-p-sm text-ink-gray-5">{{ t('rental_detail.billing.invoice_draft_hint') }}</p>
        </section>
      </template>
    </template>

    <Dialog v-model="advanceOpen" :options="{ title: t('rental_detail.billing.record_advance'), size: 'md' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl v-model="advanceForm.amount" type="number" :label="t('rental_detail.billing.amount')" size="sm" variant="subtle" />
          <FormControl
            v-model="advanceForm.mode"
            type="select"
            :label="t('rental_detail.billing.mode')"
            :options="modes.map(mode => ({ label: mode.has_account ? mode.name : `${mode.name} — ${t('rental_detail.billing.mode_no_account')}`, value: mode.name }))"
            size="sm"
            variant="subtle"
          />
          <FormControl v-model="advanceForm.reference" type="text" :label="t('rental_detail.billing.reference')" size="sm" variant="subtle" />
          <p class="text-p-sm text-ink-gray-5">{{ t('rental_detail.billing.advance_hint') }}</p>
          <p v-if="advanceError" class="text-p-sm text-ink-red-4" role="alert">{{ advanceError }}</p>
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="subtle" :disabled="recording" @click="close">{{ t('common.cancel') }}</Button>
          <Button variant="solid" :loading="recording" :disabled="!(Number(advanceForm.amount) > 0)" @click="recordAdvance">{{ t('rental_detail.billing.save_advance') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dialog, FormControl, LoadingIndicator, toast } from 'frappe-ui'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { GetRentalResponse, PaymentMode, RentalBilling } from '@/api/contracts'
import { formatDate, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const props = defineProps<{ rental: GetRentalResponse }>()
const emit = defineEmits<{ changed: [] }>()

const { t, locale } = useI18n()
const billing = ref<RentalBilling | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const modes = ref<PaymentMode[]>([])
const advanceOpen = ref(false)
const recording = ref(false)
const preparing = ref(false)
const advanceError = ref('')
const advanceForm = reactive({ amount: '', mode: '', reference: '' })

const canRecordAdvance = computed(() => props.rental.available_actions.includes('record_advance'))
const canPrepareInvoice = computed(() => props.rental.available_actions.includes('prepare_final_invoice'))

const money = (value: number) => formatMoney(value, billing.value?.currency ?? props.rental.currency, locale.value as LocaleType)
const deskUrl = (doctype: string, name: string) => `/app/${doctype}/${encodeURIComponent(name)}`
const openDesk = (doctype: string, name: string) => window.open(deskUrl(doctype, name), '_blank', 'noopener')

type PaymentLine = RentalBilling['payments'][number] & Record<string, unknown>
const paymentColumns = computed<DataTableColumn<PaymentLine>[]>(() => [
  { key: 'name', label: t('finance.invoices.number'), width: '170px' },
  { key: 'posting_date', label: t('finance.invoices.date'), width: '130px', format: row => formatDate(row.posting_date, locale.value as LocaleType) },
  { key: 'mode_of_payment', label: t('finance.invoices.mode'), width: '160px' },
  { key: 'reference_no', label: t('finance.invoices.reference'), width: '160px' },
  { key: 'docstatus', label: t('finance.invoices.state'), width: '160px' },
  { key: 'paid_amount', label: t('finance.invoices.amount'), width: '140px', align: 'right', format: row => money(row.paid_amount) }
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    billing.value = await getCortexApiClient().getRentalBilling(props.rental.id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function openAdvance() {
  advanceError.value = ''
  const outstanding = Math.max(0, (billing.value?.advance.requested ?? 0) - (billing.value?.advance.received ?? 0))
  advanceForm.amount = outstanding ? outstanding.toFixed(2) : ''
  advanceForm.reference = ''
  advanceOpen.value = true
  if (!modes.value.length) {
    try {
      modes.value = await getCortexApiClient().getPaymentModes()
      advanceForm.mode = modes.value.find(mode => mode.has_account)?.name ?? ''
    } catch (error) {
      advanceError.value = error instanceof Error ? error.message : String(error)
    }
  }
}

async function recordAdvance() {
  recording.value = true
  advanceError.value = ''
  try {
    const result = await getCortexApiClient().recordAdvancePayment({
      rental_id: props.rental.id,
      amount: Number(advanceForm.amount),
      mode_of_payment: advanceForm.mode || undefined,
      reference_no: advanceForm.reference || undefined
    })
    toast.create({
      message: result.submitted ? t('rental_detail.billing.advance_submitted', { name: result.payment_entry }) : t('rental_detail.billing.advance_drafted', { name: result.payment_entry }),
      type: result.submitted ? 'success' : 'info'
    })
    advanceOpen.value = false
    await load()
    emit('changed')
  } catch (error) {
    advanceError.value = error instanceof Error ? error.message : String(error)
  } finally {
    recording.value = false
  }
}

async function prepareInvoice() {
  preparing.value = true
  try {
    const { sales_invoice } = await getCortexApiClient().createFinalInvoice(props.rental.id)
    toast.create({ message: t('rental_detail.billing.invoice_prepared', { name: sales_invoice }), type: 'success' })
    await load()
    emit('changed')
  } catch (error) {
    toast.create({ message: error instanceof Error ? error.message : String(error), type: 'error' })
  } finally {
    preparing.value = false
  }
}

watch(() => props.rental.id, load)
onMounted(load)
defineExpose({ reload: load })
</script>
