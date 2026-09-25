<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.consignment_owners')">
      <template #title-suffix>
        <Tooltip v-if="provenance === 'mock'" :text="t('consignment_screen.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button v-if="canManage" size="sm" variant="solid" @click="openEditor()">
          <template #prefix><Plus class="size-4" :stroke-width="1.5" /></template>
          {{ t('consignment_screen.new_owner') }}
        </Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('routes.consignment_owners')">
      <TextInput v-model="search" type="search" size="sm" variant="subtle" class="lg:col-span-2" :placeholder="t('consignment_screen.search_owner')" :aria-label="t('consignment_screen.search_owner')" />
    </PageFilters>
    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div class="mt-6">
      <DataTable :label="t('routes.consignment_owners')" :columns="columns" :rows="owners" row-key="id" :loading="loading" :empty-text="t('consignment_screen.no_owners')" clickable @row-click="row => openEditor(String(row.id))">
        <template #cell-statement_status="{ row }"><StatementStatusBadge :status="row.statement_status as StatementStatus" /></template>
      </DataTable>
    </div>

    <Dialog v-model="editorOpen" :options="{ title: draft.id ? t('consignment_screen.edit_owner', { name: draft.display_name }) : t('consignment_screen.new_owner'), size: 'xl' }">
      <template #body-content>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FormControl v-model="draft.display_name" type="text" size="sm" variant="subtle" :label="t('consignment_screen.owner_name')" :disabled="!canManage" />
          <FormControl v-model="draft.owner_code" type="text" size="sm" variant="subtle" :label="t('catalog.code')" :disabled="Boolean(draft.id) || !canManage" />
          <FormControl v-model="draft.owner_type" type="select" size="sm" variant="subtle" :label="t('consignment_screen.owner_type')" :options="OWNER_TYPES.map(value => ({ label: t(`consignment_screen.type_${value.replace('-', '_')}`), value }))" :disabled="!canManage" />
          <FormControl v-model="draft.default_commission_percentage" type="number" size="sm" variant="subtle" :label="t('consignment_screen.share_label')" :disabled="!canManage" />
          <FormControl v-model="draft.contact_email" type="email" size="sm" variant="subtle" :label="t('consignment_screen.email')" :disabled="!canManage" />
          <FormControl v-model="draft.contact_phone" type="text" size="sm" variant="subtle" :label="t('consignment_screen.phone')" :disabled="!canManage" />
          <FormControl v-model="draft.billing_address" type="textarea" size="sm" variant="subtle" class="sm:col-span-2" :label="t('consignment_screen.address')" :disabled="!canManage" />
        </div>
        <div v-if="record" class="mt-5">
          <h3 class="mb-2 text-base font-semibold text-ink-gray-9">{{ t('consignment_screen.owned_units', { count: record.serials.length }) }}</h3>
          <p v-if="!record.serials.length" class="text-p-sm text-ink-gray-5">{{ t('consignment_screen.no_units') }}</p>
          <ul v-else class="max-h-40 space-y-1 overflow-auto text-base">
            <li v-for="serial in record.serials" :key="serial.serial_no">
              <RouterLink :to="{ name: 'serial-detail', params: { serial: serial.serial_no } }" class="underline decoration-outline-gray-3 underline-offset-2">{{ serial.serial_no }}</RouterLink>
              <span class="text-ink-gray-5"> · {{ serial.item_code }}</span>
            </li>
          </ul>
          <p class="mt-2 text-p-sm text-ink-gray-5">{{ t('consignment_screen.assign_hint') }}</p>
        </div>
        <p v-if="saveError" class="mt-2 text-p-sm text-ink-red-4" role="alert">{{ saveError }}</p>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="subtle" :disabled="saving" @click="close">{{ t('common.close') }}</Button>
          <Button v-if="canManage" variant="solid" :loading="saving" :disabled="!draft.display_name?.trim() || !draft.owner_code?.trim()" @click="save">{{ t('composer.save_changes') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Dialog, FormControl, TextInput, Tooltip, toast } from 'frappe-ui'
import { Plus } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { ConsignmentOwner, ConsignmentOwnerRecord, OwnerDraft, StatementStatus } from '@/api/contracts'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'
import StatementStatusBadge from '../components/StatementStatusBadge.vue'

const OWNER_TYPES = ['Third-Party', 'Co-Investment', 'House'] as const
const MANAGERS = ['System Manager', 'Cortex System Manager', 'Cortex Consignment Manager', 'Rental Manager']

const { t, locale } = useI18n()
const session = useSessionStore()

const search = ref('')
const owners = ref<ConsignmentOwner[]>([])
const provenance = ref<string | undefined>()
const loading = ref(false)
const errorMessage = ref('')
const editorOpen = ref(false)
const saving = ref(false)
const saveError = ref('')
const record = ref<ConsignmentOwnerRecord | null>(null)
const draft = reactive<OwnerDraft>({})

const canManage = computed(() => MANAGERS.some(role => session.hasRole(role)))
const money = (value: number) => formatMoney(value, session.activeCompany?.currency, locale.value as LocaleType)

const columns = computed<DataTableColumn<ConsignmentOwner>[]>(() => [
  { key: 'display_name', label: t('consignment_screen.owner'), width: '260px' },
  { key: 'owner_code', label: t('catalog.code'), width: '110px' },
  { key: 'owner_type', label: t('consignment_screen.owner_type'), width: '150px', format: row => t(`consignment_screen.type_${row.owner_type.replace('-', '_')}`) },
  { key: 'default_commission_percentage', label: t('consignment_screen.share'), width: '100px', align: 'right', format: row => `${row.default_commission_percentage} %` },
  { key: 'active_serials_count', label: t('consignment_screen.units'), width: '90px', align: 'right' },
  { key: 'period_amount_due', label: t('consignment_screen.amount_due'), width: '150px', align: 'right', format: row => money(row.period_amount_due) },
  { key: 'statement_status', label: t('consignment_screen.statement'), width: '150px' }
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getCortexApiClient().listOwners({ search: search.value || undefined })
    owners.value = result.items
    provenance.value = result.provenance
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function openEditor(ownerId?: string) {
  saveError.value = ''
  record.value = null
  for (const key of Object.keys(draft)) delete (draft as Record<string, unknown>)[key]
  Object.assign(draft, { owner_type: 'Third-Party', default_commission_percentage: 70 })
  editorOpen.value = true
  if (!ownerId) return
  try {
    record.value = await getCortexApiClient().getOwner(ownerId)
    const r = record.value
    Object.assign(draft, { id: r.id, owner_code: r.owner_code, display_name: r.display_name, owner_type: r.owner_type, default_commission_percentage: r.default_commission_percentage, contact_email: r.contact_email, contact_phone: r.contact_phone, billing_address: r.billing_address })
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : String(error)
  }
}

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    record.value = await getCortexApiClient().saveOwner({ ...draft, default_commission_percentage: Number(draft.default_commission_percentage) })
    toast.create({ message: t('consignment_screen.owner_saved'), type: 'success' })
    editorOpen.value = false
    await load()
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : String(error)
  } finally {
    saving.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(search, () => { clearTimeout(timer); timer = setTimeout(load, 250) })
onMounted(load)
</script>
