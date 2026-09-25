<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.kits_list')">
      <template #actions>
        <Checkbox v-model="includeInactive" :label="t('kits.include_inactive')" />
        <Button v-if="canEdit" size="sm" variant="solid" @click="openEditor()">
          <template #prefix><Plus class="size-4" :stroke-width="1.5" /></template>
          {{ t('kits.new_kit') }}
        </Button>
      </template>
    </PageHeader>

    <p class="px-6 pt-4 text-p-base text-ink-gray-6">{{ t('kits.explanation') }}</p>
    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div class="mt-6">
      <DataTable :label="t('routes.kits_list')" :columns="columns" :rows="rows" row-key="name" :loading="loading" :empty-text="t('kits.empty')" :clickable="canEdit" @row-click="row => openEditor(row.kit)">
        <template #cell-is_active="{ row }">
          <Badge :theme="row.is_active ? 'green' : 'gray'" variant="subtle">{{ row.is_active ? t('kits.active') : t('kits.inactive') }}</Badge>
        </template>
      </DataTable>
    </div>

    <Dialog v-model="editorOpen" :options="{ title: draft.name ? t('kits.edit_kit', { name: draft.kit_name }) : t('kits.new_kit'), size: '3xl' }">
      <template #body-content>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <FormControl v-model="draft.kit_name" type="text" size="sm" variant="subtle" class="sm:col-span-2" :label="t('kits.kit_name')" />
          <FormControl v-model="draft.discount_percentage" type="number" size="sm" variant="subtle" :label="t('kits.discount')" />
          <FormControl v-model="draft.description" type="textarea" size="sm" variant="subtle" class="sm:col-span-3" :label="t('kits.description')" />
          <Checkbox v-model="draft.is_active" :label="t('kits.active')" />
        </div>

        <div class="relative mt-5">
          <TextInput v-model="query" type="search" size="sm" variant="subtle" :placeholder="t('composer.add_item')" :aria-label="t('composer.add_item')" @focus="catalogOpen = true" @blur="closeSoon" />
          <ul v-if="catalogOpen && catalog.length" class="absolute z-30 mt-1 max-h-60 w-full overflow-auto rounded bg-surface-white py-1 shadow-xl ring-1 ring-outline-gray-1" role="listbox">
            <li v-for="item in catalog" :key="item.item_code" role="option" :aria-selected="false">
              <button type="button" class="flex w-full justify-between gap-3 px-3 py-1.5 text-left text-base hover:bg-surface-gray-2" @mousedown.prevent="addComponent(item.item_code, item.item_name, item.daily_rate)">
                <span class="truncate">{{ item.item_name }} <span class="text-ink-gray-5">· {{ item.item_code }}</span></span>
                <span class="shrink-0 text-sm text-ink-gray-6">{{ t('composer.per_day', { rate: money(item.daily_rate) }) }}</span>
              </button>
            </li>
          </ul>
        </div>

        <table class="mt-3 w-full border-collapse border-t border-outline-gray-1 text-base">
          <thead>
            <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
              <th class="px-[7.5px] text-left font-normal">{{ t('rental_detail.item') }}</th>
              <th class="w-[100px] px-[7.5px] text-right font-normal">{{ t('rental_detail.qty') }}</th>
              <th class="w-[110px] px-[7.5px] text-center font-normal">{{ t('kits.optional') }}</th>
              <th class="w-[130px] px-[7.5px] text-right font-normal">{{ t('rental_detail.daily_rate') }}</th>
              <th class="w-[44px]"><span class="sr-only">{{ t('composer.remove') }}</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!draft.items.length" class="h-[33px]"><td colspan="5" class="px-4 py-6 text-center text-ink-gray-5">{{ t('kits.no_components') }}</td></tr>
            <tr v-for="(component, index) in draft.items" :key="component.item_code" class="h-[33px] border-b border-outline-gray-1">
              <td class="px-[7.5px]">{{ component.item_name }} <span class="text-ink-gray-5">· {{ component.item_code }}</span></td>
              <td class="px-1"><input v-model.number="component.qty" type="number" min="1" class="h-6 w-full rounded border-0 bg-surface-gray-2 px-1.5 text-right" :aria-label="t('composer.qty_for', { item: component.item_name })" /></td>
              <td class="text-center"><input v-model="component.is_optional" type="checkbox" class="rounded text-ink-gray-9 focus:ring-outline-gray-3" :aria-label="t('kits.optional_for', { item: component.item_name })" /></td>
              <td class="px-[7.5px] text-right tabular-nums">{{ money(component.daily_rate) }}</td>
              <td class="text-center"><button type="button" class="rounded p-1 text-ink-gray-5 hover:text-ink-red-4" :aria-label="t('composer.remove_item', { item: component.item_name })" @click="draft.items.splice(index, 1)"><X class="size-4" :stroke-width="1.5" /></button></td>
            </tr>
          </tbody>
        </table>
        <p class="mt-3 text-right text-base">{{ t('kits.kit_price', { price: money(kitPrice) }) }}</p>
        <p v-if="saveError" class="mt-2 text-p-sm text-ink-red-4" role="alert">{{ saveError }}</p>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="subtle" :disabled="saving" @click="close">{{ t('common.cancel') }}</Button>
          <Button variant="solid" :loading="saving" :disabled="!draft.kit_name.trim() || !draft.items.length" @click="save">{{ t('composer.save_changes') }}</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Checkbox, Dialog, FormControl, TextInput, toast } from 'frappe-ui'
import { Plus, X } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { RentalCatalogOption, RentalKit } from '@/api/contracts'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'
import { useSessionStore } from '@/stores/session'

const { t, locale } = useI18n()
const session = useSessionStore()
const api = getCortexApiClient()

const kits = ref<RentalKit[]>([])
const includeInactive = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const editorOpen = ref(false)
const saving = ref(false)
const saveError = ref('')
const query = ref('')
const catalog = ref<RentalCatalogOption[]>([])
const catalogOpen = ref(false)
const draft = reactive<RentalKit>({ kit_name: '', is_active: true, discount_percentage: 0, description: '', items: [] })

const canEdit = computed(() => session.hasPermission('cortex:catalog:manage'))
const money = (value: number) => formatMoney(value, session.activeCompany?.currency, locale.value as LocaleType)
const kitPrice = computed(() => draft.items.filter(item => !item.is_optional).reduce((sum, item) => sum + item.daily_rate * (item.qty || 0), 0) * (1 - (Number(draft.discount_percentage) || 0) / 100))

interface KitRow extends Record<string, unknown> { name: string; kit_name: string; components: string; discount: string; is_active: boolean; kit: RentalKit }
const rows = computed<KitRow[]>(() => kits.value.map(kit => ({
  name: kit.name ?? kit.kit_name,
  kit_name: kit.kit_name,
  components: kit.items.map(item => `${item.qty} × ${item.item_name}${item.is_optional ? ` (${t('kits.optional').toLowerCase()})` : ''}`).join(', '),
  discount: kit.discount_percentage ? `${kit.discount_percentage} %` : '',
  is_active: kit.is_active,
  kit
})))
const columns = computed<DataTableColumn<KitRow>[]>(() => [
  { key: 'kit_name', label: t('kits.kit_name'), width: '240px' },
  { key: 'components', label: t('kits.components') },
  { key: 'discount', label: t('kits.discount'), width: '110px', align: 'right' },
  { key: 'is_active', label: t('finance.invoices.state'), width: '120px' }
])

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    kits.value = await api.listKits({ include_inactive: includeInactive.value })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function openEditor(kit?: RentalKit) {
  Object.assign(draft, kit ? structuredClone(kit) : { name: undefined, kit_name: '', is_active: true, discount_percentage: 0, description: '', items: [] })
  saveError.value = ''
  editorOpen.value = true
}

function addComponent(itemCode: string, itemName: string, dailyRate: number) {
  const existing = draft.items.find(item => item.item_code === itemCode)
  if (existing) existing.qty += 1
  else draft.items.push({ item_code: itemCode, item_name: itemName, qty: 1, is_optional: false, daily_rate: dailyRate })
  query.value = ''
  catalogOpen.value = false
}
const closeSoon = () => setTimeout(() => (catalogOpen.value = false), 150)

let timer: ReturnType<typeof setTimeout> | undefined
watch(query, value => {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    try { catalog.value = await api.searchRentalCatalog(value.trim()) } catch { catalog.value = [] }
  }, 250)
})

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    await api.saveKit({ ...draft, discount_percentage: Number(draft.discount_percentage) || 0 })
    toast.create({ message: t('kits.saved', { name: draft.kit_name }), type: 'success' })
    editorOpen.value = false
    await load()
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : String(error)
  } finally {
    saving.value = false
  }
}

watch(includeInactive, () => void load())
onMounted(load)
</script>
