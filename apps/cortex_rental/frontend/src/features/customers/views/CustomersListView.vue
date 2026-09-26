<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.customers_list')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock'" :text="t('customers.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button size="sm" variant="solid" @click="openCreate">
          <template #prefix><Plus class="size-4" :stroke-width="1.5" /></template>
          {{ t('customers.new_customer') }}
        </Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('routes.customers_list')">
      <TextInput v-model="search" type="search" size="sm" variant="subtle" class="lg:col-span-2" :placeholder="t('customers.search')" :aria-label="t('customers.search')" />
    </PageFilters>
    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div class="mt-6">
      <DataTable
        :label="t('routes.customers_list')"
        :columns="columns"
        :rows="rows"
        row-key="name"
        :loading="loading"
        :empty-text="t('customers.empty')"
        :total="total"
        :page="page"
        :page-size="pageSize"
        clickable
        @row-click="row => router.push({ name: 'customer-detail', params: { customer: String(row.name) } })"
        @update:page="value => (page = value)"
        @update:page-size="value => { pageSize = value; page = 1 }"
      >
        <template #cell-insurance_status="{ row }"><InsuranceBadge :status="row.insurance_status as InsuranceStatus" :valid-until="row.insurance_valid_until as string | null" /></template>
      </DataTable>
    </div>

    <Dialog v-model="createOpen" :options="{ title: t('customers.new_customer'), size: 'md' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl v-model="form.customer_name" type="text" size="sm" variant="subtle" :label="t('customers.name')" />
          <FormControl v-model="form.customer_type" type="select" size="sm" variant="subtle" :label="t('customers.type')" :options="[{ label: t('customers.type_Company'), value: 'Company' }, { label: t('customers.type_Individual'), value: 'Individual' }]" />
          <FormControl v-model="form.email" type="email" size="sm" variant="subtle" :label="t('consignment_screen.email')" />
          <FormControl v-model="form.phone" type="text" size="sm" variant="subtle" :label="t('consignment_screen.phone')" />
          <p class="text-p-sm text-ink-gray-5">{{ t('customers.create_hint') }}</p>
          <p v-if="createError" class="text-p-sm text-ink-red-4" role="alert">{{ createError }}</p>
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="subtle" :disabled="creating" @click="close">{{ t('common.cancel') }}</Button>
          <Button variant="solid" :loading="creating" :disabled="form.customer_name.trim().length < 2" @click="create">{{ t('customers.create') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dialog, FormControl, TextInput, Tooltip, toast } from 'frappe-ui'
import { Plus } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { CustomerRow, InsuranceStatus, NewCustomerInput } from '@/api/contracts'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import InsuranceBadge from '../components/InsuranceBadge.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const search = ref(typeof route.query.q === 'string' ? route.query.q : '')
const page = ref(1)
const pageSize = ref(100)
const rows = ref<CustomerRow[]>([])
const total = ref(0)
const currency = ref<string | null>(null)
const provenance = ref<string | undefined>()
const loading = ref(false)
const errorMessage = ref('')
const createOpen = ref(false)
const creating = ref(false)
const createError = ref('')
const form = reactive<NewCustomerInput>({ customer_name: '', customer_type: 'Company', email: '', phone: '' })

const columns = computed<DataTableColumn<CustomerRow>[]>(() => [
  { key: 'customer_name', label: t('customers.name'), width: '280px' },
  { key: 'email', label: t('consignment_screen.email'), width: '240px' },
  { key: 'phone', label: t('consignment_screen.phone'), width: '150px' },
  { key: 'rentals', label: t('customers.rentals'), width: '100px', align: 'right' },
  { key: 'active_rentals', label: t('customers.active'), width: '100px', align: 'right' },
  { key: 'outstanding', label: t('finance.invoices.outstanding'), width: '140px', align: 'right', format: row => formatMoney(row.outstanding, currency.value, locale.value as LocaleType) },
  { key: 'insurance_status', label: t('customers.insurance'), width: '180px' }
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().listCustomers({ search: search.value || undefined, page: page.value, page_size: pageSize.value })
    rows.value = result.items
    total.value = result.total_count
    currency.value = result.currency
    provenance.value = result.provenance
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, { customer_name: '', customer_type: 'Company', email: '', phone: '' })
  createError.value = ''
  createOpen.value = true
}

async function create() {
  creating.value = true
  createError.value = ''
  try {
    const record = await getCortexApiClient().createCustomer({ ...form, email: form.email || undefined, phone: form.phone || undefined })
    toast.create({ message: t('customers.created', { name: record.customer_name }), type: 'success' })
    createOpen.value = false
    await router.push({ name: 'customer-detail', params: { customer: record.name } })
  } catch (error) {
    createError.value = error instanceof Error ? error.message : String(error)
  } finally {
    creating.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
  page.value = 1
  void router.replace({ query: { q: search.value || undefined } })
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})
watch([page, pageSize], () => void load())
onMounted(load)
</script>
