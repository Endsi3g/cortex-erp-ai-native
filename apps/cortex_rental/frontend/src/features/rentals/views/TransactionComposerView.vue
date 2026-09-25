<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="editing ? t('composer.edit_title', { name: editing.id }) : t('routes.rental_composer')">
      <template #title-suffix>
        <Badge v-if="dirty" theme="orange" variant="subtle">{{ t('composer.not_saved') }}</Badge>
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" @click="router.back()">{{ t('common.cancel') }}</Button>
        <Button size="sm" variant="solid" :loading="saving" :disabled="!canSave" @click="save">
          {{ editing ? t('composer.save_changes') : t('composer.create_quote') }}
        </Button>
      </template>
    </PageHeader>

    <p v-if="saveError" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ saveError }}</p>

    <!-- Customer & period -->
    <section class="border-b border-outline-gray-1 px-6 py-5" :aria-labelledby="`${uid}-customer`">
      <h2 :id="`${uid}-customer`" class="mb-4 text-base font-semibold text-ink-gray-9">{{ t('composer.section_customer') }}</h2>
      <div class="grid grid-cols-1 gap-x-4 gap-y-5 md:grid-cols-2 xl:grid-cols-4">
        <div class="relative">
          <label class="mb-1.5 block text-sm text-ink-gray-5" :for="`${uid}-customer-input`">{{ t('composer.customer') }} *</label>
          <TextInput
            :id="`${uid}-customer-input`"
            v-model="customerQuery"
            type="search"
            size="sm"
            variant="subtle"
            autocomplete="off"
            :placeholder="t('composer.customer_placeholder')"
            :disabled="Boolean(editing)"
            @focus="customerOpen = true"
            @blur="closeCustomerSoon"
          />
          <ul
            v-if="customerOpen && customers.length"
            class="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded bg-surface-white py-1 shadow-xl ring-1 ring-outline-gray-1"
            role="listbox"
          >
            <li v-for="customer in customers" :key="customer.id" role="option" :aria-selected="customer.id === form.customerId">
              <button type="button" class="flex w-full items-center justify-between px-3 py-1.5 text-left text-base hover:bg-surface-gray-2" @mousedown.prevent="pickCustomer(customer)">
                <span class="truncate">{{ customer.name }}</span>
                <span v-if="customer.insurance_valid === false" class="text-sm text-ink-red-4">{{ t('composer.insurance_expired') }}</span>
              </button>
            </li>
          </ul>
          <p v-if="selectedCustomer?.insurance_valid === false" class="mt-1.5 text-p-sm text-ink-red-4">{{ t('composer.insurance_warning') }}</p>
          <p v-else-if="selectedCustomer?.insurance_valid === null" class="mt-1.5 text-p-sm text-ink-gray-5">{{ t('composer.insurance_unknown') }}</p>
        </div>
        <div>
          <label class="mb-1.5 block text-sm text-ink-gray-5" :for="`${uid}-project`">{{ t('composer.project') }}</label>
          <TextInput :id="`${uid}-project`" v-model="form.projectName" size="sm" variant="subtle" />
        </div>
        <div>
          <label class="mb-1.5 block text-sm text-ink-gray-5" :for="`${uid}-start`">{{ t('composer.starts_at') }} *</label>
          <TextInput :id="`${uid}-start`" v-model="form.startsAt" type="datetime-local" size="sm" variant="subtle" />
        </div>
        <div>
          <label class="mb-1.5 block text-sm text-ink-gray-5" :for="`${uid}-end`">{{ t('composer.ends_at') }} *</label>
          <TextInput :id="`${uid}-end`" v-model="form.endsAt" type="datetime-local" size="sm" variant="subtle" :min="form.startsAt" />
          <p v-if="periodError" class="mt-1.5 text-p-sm text-ink-red-4">{{ periodError }}</p>
        </div>
      </div>
    </section>

    <!-- Equipment -->
    <section class="py-5" :aria-labelledby="`${uid}-items`">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-3 px-6">
        <h2 :id="`${uid}-items`" class="text-base font-semibold text-ink-gray-9">{{ t('composer.section_items') }}</h2>
        <div class="relative w-full max-w-md">
          <TextInput
            v-model="catalogQuery"
            type="search"
            size="sm"
            variant="subtle"
            autocomplete="off"
            :placeholder="t('composer.add_item')"
            :aria-label="t('composer.add_item')"
            @focus="catalogOpen = true"
            @blur="closeCatalogSoon"
          />
          <ul v-if="catalogOpen && catalog.length" class="absolute right-0 z-20 mt-1 max-h-72 w-full overflow-auto rounded bg-surface-white py-1 shadow-xl ring-1 ring-outline-gray-1" role="listbox">
            <li v-for="item in catalog" :key="item.item_code" role="option" :aria-selected="false">
              <button type="button" class="flex w-full items-center justify-between gap-3 px-3 py-1.5 text-left text-base hover:bg-surface-gray-2" @mousedown.prevent="addItem(item.item_code, item.item_name)">
                <span class="min-w-0 truncate">{{ item.item_name }} <span class="text-ink-gray-5">· {{ item.item_code }}</span></span>
                <span class="shrink-0 text-sm tabular-nums text-ink-gray-6">{{ t('composer.per_day', { rate: money(item.daily_rate) }) }}</span>
              </button>
            </li>
          </ul>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full min-w-max border-collapse border-t border-outline-gray-1 text-base text-ink-gray-8">
          <thead>
            <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
              <th class="w-[37px] border-r border-outline-gray-1 font-normal"><span class="sr-only">#</span></th>
              <th class="border-r border-outline-gray-1 px-[7.5px] text-left font-normal">{{ t('rental_detail.item') }}</th>
              <th class="w-[90px] border-r border-outline-gray-1 px-[7.5px] text-right font-normal">{{ t('rental_detail.qty') }}</th>
              <th class="w-[130px] border-r border-outline-gray-1 px-[7.5px] text-right font-normal">{{ t('rental_detail.daily_rate') }}</th>
              <th class="w-[100px] border-r border-outline-gray-1 px-[7.5px] text-right font-normal">{{ t('rental_detail.discount') }}</th>
              <th class="w-[110px] border-r border-outline-gray-1 px-[7.5px] text-right font-normal">{{ t('rentals.col_billable_days') }}</th>
              <th class="w-[140px] border-r border-outline-gray-1 px-[7.5px] text-right font-normal">{{ t('rental_detail.amount') }}</th>
              <th class="w-[220px] border-r border-outline-gray-1 px-[7.5px] text-left font-normal">{{ t('composer.availability') }}</th>
              <th class="w-[44px]"><span class="sr-only">{{ t('composer.remove') }}</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!lines.length" class="h-[33px]">
              <td colspan="9" class="px-4 py-8 text-center text-ink-gray-5">{{ t('composer.no_items') }}</td>
            </tr>
            <template v-for="(line, index) in lines" :key="line.itemCode">
              <tr class="h-[33px] border-b border-outline-gray-1">
                <td class="border-r border-outline-gray-1 text-center tabular-nums">{{ index + 1 }}</td>
                <td class="border-r border-outline-gray-1 px-[7.5px]">{{ line.itemName }} <span class="text-ink-gray-5">· {{ line.itemCode }}</span></td>
                <td class="border-r border-outline-gray-1 px-1">
                  <input v-model.number="line.quantity" type="number" min="1" step="1" class="h-6 w-full rounded border-0 bg-surface-gray-2 px-1.5 text-right text-base tabular-nums focus:ring-1 focus:ring-outline-gray-3" :aria-label="t('composer.qty_for', { item: line.itemName })" />
                </td>
                <td class="border-r border-outline-gray-1 px-[7.5px] text-right tabular-nums">{{ priced(line.itemCode) ? money(priced(line.itemCode)!.daily_rate) : '—' }}</td>
                <td class="border-r border-outline-gray-1 px-1">
                  <input v-model.number="line.discount" type="number" min="0" max="100" step="0.5" class="h-6 w-full rounded border-0 bg-surface-gray-2 px-1.5 text-right text-base tabular-nums focus:ring-1 focus:ring-outline-gray-3" :aria-label="t('composer.discount_for', { item: line.itemName })" />
                </td>
                <td class="border-r border-outline-gray-1 px-[7.5px] text-right tabular-nums">{{ pricing ? pricing.billable_days : '—' }}</td>
                <td class="border-r border-outline-gray-1 px-[7.5px] text-right tabular-nums">{{ priced(line.itemCode) ? money(priced(line.itemCode)!.line_subtotal) : '—' }}</td>
                <td class="border-r border-outline-gray-1 px-[7.5px]">
                  <template v-if="stock(line.itemCode)">
                    <span v-if="stock(line.itemCode)!.is_available" class="text-ink-green-3">{{ t('composer.available', { qty: stock(line.itemCode)!.available_quantity }) }}</span>
                    <button v-else type="button" class="text-left text-ink-red-4 underline decoration-dotted underline-offset-2" @click="loadAlternatives(line.itemCode)">
                      {{ t('composer.unavailable', { qty: stock(line.itemCode)!.available_quantity }) }}
                    </button>
                  </template>
                  <span v-else class="text-ink-gray-5">{{ checking ? t('composer.checking') : '—' }}</span>
                </td>
                <td class="text-center">
                  <button type="button" class="rounded p-1 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-red-4" :aria-label="t('composer.remove_item', { item: line.itemName })" @click="lines.splice(index, 1)">
                    <X class="size-4" :stroke-width="1.5" />
                  </button>
                </td>
              </tr>
              <tr v-if="alternatives[line.itemCode]" class="border-b border-outline-gray-1 bg-surface-gray-1">
                <td />
                <td colspan="8" class="px-[7.5px] py-2">
                  <p class="text-sm text-ink-gray-6">{{ t('composer.alternatives_title') }}</p>
                  <p v-if="!alternatives[line.itemCode]!.length" class="text-p-sm text-ink-gray-5">{{ t('composer.no_alternatives') }}</p>
                  <div class="mt-1.5 flex flex-wrap gap-2">
                    <Button v-for="alt in alternatives[line.itemCode]" :key="alt.item_code" size="sm" variant="subtle" @click="replaceItem(line.itemCode, alt.item_code, alt.item_name)">
                      {{ alt.item_name }} · {{ t('composer.available', { qty: alt.available_quantity }) }} · {{ t('composer.per_day', { rate: money(alt.daily_rate) }) }}
                    </Button>
                  </div>
                  <p class="mt-1.5 text-p-sm text-ink-gray-5">{{ t('composer.alternatives_hint') }}</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <p v-if="checkError" class="mx-6 mt-3 text-p-sm text-ink-red-4" role="alert">{{ checkError }}</p>
    </section>

    <!-- Totals & notes -->
    <section class="grid grid-cols-1 gap-6 border-t border-outline-gray-1 px-6 py-5 lg:grid-cols-2">
      <div>
        <label class="mb-1.5 block text-sm text-ink-gray-5" :for="`${uid}-notes`">{{ t('composer.notes') }}</label>
        <textarea :id="`${uid}-notes`" v-model="form.notes" rows="4" class="w-full rounded border-0 bg-surface-gray-2 px-2 py-1.5 text-base text-ink-gray-8 focus:ring-2 focus:ring-outline-gray-3" />
      </div>
      <dl class="space-y-1.5 text-base lg:ml-auto lg:w-full lg:max-w-sm">
        <div class="flex justify-between"><dt class="text-ink-gray-6">{{ t('rental_detail.subtotal') }}</dt><dd class="tabular-nums">{{ pricing ? money(pricing.subtotal) : '—' }}</dd></div>
        <div v-if="pricing?.discount_amount" class="flex justify-between"><dt class="text-ink-gray-6">{{ t('rental_detail.discounts') }}</dt><dd class="tabular-nums">− {{ money(pricing.discount_amount) }}</dd></div>
        <div v-for="tax in pricing?.tax_lines ?? []" :key="tax.description" class="flex justify-between">
          <dt class="text-ink-gray-6">{{ tax.description }} ({{ new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(tax.rate) }} %)</dt><dd class="tabular-nums">{{ money(tax.amount) }}</dd>
        </div>
        <div class="flex justify-between border-t border-outline-gray-1 pt-1.5 font-semibold text-ink-gray-9"><dt>{{ t('composer.estimated_total') }}</dt><dd class="tabular-nums">{{ pricing ? money(pricing.grand_total) : '—' }}</dd></div>
        <p class="pt-1 text-p-sm text-ink-gray-5">
          {{ pricing && !pricing.tax_template ? t('composer.no_tax_template') : pricing && pricing.tax_estimate_complete === false ? t('composer.tax_partial') : t('composer.tax_note') }}
        </p>
        <p v-if="pricing" class="text-p-sm text-ink-gray-5">{{ pricing.pricing_rule_applied }} · {{ t('rental_detail.days_value', { calendar: pricing.calendar_days, billable: pricing.billable_days }) }}</p>
      </dl>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, useId, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, TextInput, toast } from 'frappe-ui'
import { X } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import { getCortexApiClient } from '@/api'
import type {
  AlternativesResponse,
  AvailabilityCheckResponse,
  GetRentalResponse,
  PreviewPricingResponse,
  RentalCatalogOption,
  RentalCustomerOption
} from '@/api/contracts'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'

interface Line { itemCode: string; itemName: string; quantity: number; discount: number }

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const uid = useId()
const api = getCortexApiClient()

const editing = ref<GetRentalResponse | null>(null)
const form = reactive({ customerId: '', projectName: '', startsAt: '', endsAt: '', notes: '' })
const lines = ref<Line[]>([])
const dirty = ref(false)

const customerQuery = ref('')
const customers = ref<RentalCustomerOption[]>([])
const customerOpen = ref(false)
const selectedCustomer = ref<RentalCustomerOption | null>(null)

const catalogQuery = ref('')
const catalog = ref<RentalCatalogOption[]>([])
const catalogOpen = ref(false)

const pricing = ref<PreviewPricingResponse | null>(null)
const availability = ref<AvailabilityCheckResponse | null>(null)
const alternatives = reactive<Record<string, AlternativesResponse['alternatives'] | undefined>>({})
const checking = ref(false)
const checkError = ref('')
const saving = ref(false)
const saveError = ref('')

const session = useSessionStore()
const money = (value: number) => formatMoney(value, session.activeCompany?.currency, locale.value as LocaleType)
const iso = (value: string) => (value.length === 16 ? `${value}:00` : value).replace('T', ' ')
const localInput = (value: string) => value.replace(' ', 'T').slice(0, 16)

const periodError = computed(() => (form.startsAt && form.endsAt && form.endsAt <= form.startsAt ? t('composer.period_invalid') : ''))
const allAvailable = computed(() => Boolean(availability.value?.all_available))
const canSave = computed(() =>
  Boolean(form.customerId && form.startsAt && form.endsAt && !periodError.value && lines.value.length && pricing.value && allAvailable.value && !checking.value && !saving.value)
)

const priced = (code: string) => pricing.value?.lines.find(line => line.item_code === code)
const stock = (code: string) => availability.value?.items.find(item => item.item_code === code)

// ---- customer & catalog search -------------------------------------------------
let customerTimer: ReturnType<typeof setTimeout> | undefined
watch(customerQuery, value => {
  if (selectedCustomer.value && value === selectedCustomer.value.name) return
  form.customerId = ''
  selectedCustomer.value = null
  clearTimeout(customerTimer)
  customerTimer = setTimeout(async () => {
    try { customers.value = await api.searchRentalCustomers(value.trim()) } catch { customers.value = [] }
  }, 250)
})
function pickCustomer(customer: RentalCustomerOption) {
  selectedCustomer.value = customer
  form.customerId = customer.id
  customerQuery.value = customer.name
  customerOpen.value = false
  dirty.value = true
}
const closeCustomerSoon = () => setTimeout(() => (customerOpen.value = false), 150)

let catalogTimer: ReturnType<typeof setTimeout> | undefined
watch(catalogQuery, value => {
  clearTimeout(catalogTimer)
  catalogTimer = setTimeout(async () => {
    try { catalog.value = await api.searchRentalCatalog(value.trim()) } catch { catalog.value = [] }
  }, 250)
})
const closeCatalogSoon = () => setTimeout(() => (catalogOpen.value = false), 150)

function addItem(code: string, name: string) {
  const existing = lines.value.find(line => line.itemCode === code)
  if (existing) existing.quantity += 1
  else lines.value.push({ itemCode: code, itemName: name, quantity: 1, discount: 0 })
  catalogQuery.value = ''
  catalogOpen.value = false
}

function replaceItem(from: string, code: string, name: string) {
  const line = lines.value.find(item => item.itemCode === from)
  if (!line) return
  delete alternatives[from]
  if (lines.value.some(item => item.itemCode === code)) {
    lines.value = lines.value.filter(item => item.itemCode !== from)
    addItem(code, name)
  } else {
    line.itemCode = code
    line.itemName = name
  }
}

async function loadAlternatives(code: string) {
  try {
    alternatives[code] = (await api.getAvailabilityAlternatives({ item_code: code, starts_at: iso(form.startsAt), ends_at: iso(form.endsAt) })).alternatives
  } catch (error) {
    checkError.value = error instanceof Error ? error.message : String(error)
  }
}

// ---- live server pricing + availability ----------------------------------------
let refreshTimer: ReturnType<typeof setTimeout> | undefined
let sequence = 0
watch([lines, () => form.startsAt, () => form.endsAt], () => {
  dirty.value = true
  clearTimeout(refreshTimer)
  refreshTimer = setTimeout(refresh, 350)
}, { deep: true })

async function refresh() {
  pricing.value = null
  availability.value = null
  checkError.value = ''
  if (!lines.value.length || !form.startsAt || !form.endsAt || periodError.value) return
  const current = ++sequence
  checking.value = true
  const items = lines.value.map(line => ({ item_code: line.itemCode, quantity: Math.max(1, Math.round(line.quantity || 1)), discount_percentage: line.discount || 0 }))
  try {
    const [price, stockResult] = await Promise.all([
      api.previewPricing({ starts_at: iso(form.startsAt), ends_at: iso(form.endsAt), items }),
      api.checkInventoryAvailability({ starts_at: iso(form.startsAt), ends_at: iso(form.endsAt), items: items.map(({ item_code, quantity }) => ({ item_code, quantity })) })
    ])
    if (current !== sequence) return
    pricing.value = price
    availability.value = stockResult
  } catch (error) {
    if (current === sequence) checkError.value = error instanceof Error ? error.message : String(error)
  } finally {
    if (current === sequence) checking.value = false
  }
}

// ---- save ----------------------------------------------------------------------
async function save() {
  saving.value = true
  saveError.value = ''
  const items = lines.value.map(line => ({ item_code: line.itemCode, quantity: Math.round(line.quantity), discount_percentage: line.discount || 0 }))
  try {
    const result = editing.value
      ? await api.updateQuoteDraft({ rental_id: editing.value.id, version: editing.value.version, starts_at: iso(form.startsAt), ends_at: iso(form.endsAt), project_name: form.projectName, notes: form.notes, items })
      : await api.createQuoteDraft({ customer_id: form.customerId, starts_at: iso(form.startsAt), ends_at: iso(form.endsAt), project_name: form.projectName || undefined, notes: form.notes || undefined, items })
    if (result.status !== 'completed' || !result.entity_id) throw new Error(result.errors?.[0]?.message ?? t('rental_detail.action_refused'))
    dirty.value = false
    toast.create({ message: editing.value ? t('composer.saved') : t('composer.created', { name: result.entity_id }), type: 'success' })
    await router.push({ name: 'rental-detail', params: { name: result.entity_id } })
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : String(error)
  } finally {
    saving.value = false
  }
}

// ---- prefill: edit mode (?rental=) or from availability (?items=&starts_at=&ends_at=) ----
function defaultPeriod() {
  const start = new Date()
  start.setDate(start.getDate() + 1)
  const day = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}-${String(start.getDate()).padStart(2, '0')}`
  const end = new Date(start)
  end.setDate(end.getDate() + 2)
  const endDay = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, '0')}-${String(end.getDate()).padStart(2, '0')}`
  return { startsAt: `${day}T08:00`, endsAt: `${endDay}T18:00` }
}

onMounted(async () => {
  const rentalId = typeof route.query.rental === 'string' ? route.query.rental : ''
  if (rentalId) {
    try {
      const rental = await api.getRental({ id: rentalId })
      editing.value = rental
      form.customerId = rental.customer_id
      selectedCustomer.value = { id: rental.customer_id, name: rental.customer_name, insurance_valid: null }
      customerQuery.value = rental.customer_name
      form.projectName = rental.project_name ?? ''
      form.startsAt = localInput(rental.starts_at)
      form.endsAt = localInput(rental.ends_at)
      form.notes = rental.notes ?? ''
      lines.value = rental.items.map(item => ({ itemCode: item.item_code, itemName: item.item_name, quantity: item.quantity, discount: item.discount_percentage }))
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : String(error)
    }
  } else {
    const period = defaultPeriod()
    form.startsAt = typeof route.query.starts_at === 'string' ? `${route.query.starts_at.slice(0, 10)}T08:00` : period.startsAt
    form.endsAt = typeof route.query.ends_at === 'string' ? `${route.query.ends_at.slice(0, 10)}T18:00` : period.endsAt
    const codes = typeof route.query.items === 'string' ? route.query.items.split(',').map(code => code.trim()).filter(Boolean) : []
    for (const code of codes) {
      try {
        const match = (await api.searchRentalCatalog(code)).find(item => item.item_code === code)
        if (match) addItem(match.item_code, match.item_name)
      } catch { /* unknown code: ignored, nothing invented */ }
    }
  }
  dirty.value = false
})
</script>
