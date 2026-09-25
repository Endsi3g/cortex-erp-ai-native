<template>
  <div class="space-y-5" data-test="step-client-dates">
    <div class="space-y-1.5">
      <label class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">{{ t('composer.client_label') }} *</label>
      <input v-model="customerQuery" type="search" autocomplete="off" :placeholder="t('composer.select_client')" class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface" data-test="customer-search" @input="searchCustomers" />
      <div v-if="customerQuery && customers.length" class="max-h-48 overflow-auto rounded-lg border border-cortex-border bg-white">
        <button v-for="cust in customers" :key="cust.id" type="button" class="block w-full px-3 py-2 text-left text-xs hover:bg-cortex-surface-secondary" @click="selectCustomer(cust)">{{ cust.name }} <span class="text-cortex-text-muted">· {{ cust.id }}</span></button>
      </div>
      <p v-if="customersLoading" class="text-[11px] text-cortex-text-muted">Recherche des clients dans ERPNext…</p>
      <p v-if="modelValue.customerId" class="text-[11px] text-cortex-primary-700">Client ERPNext sélectionné : {{ modelValue.customerName }} · assurance {{ selectedCustomer?.insurance_valid === true ? 'valide' : selectedCustomer?.insurance_valid === false ? 'à corriger' : 'à vérifier' }}</p>
      <p v-else class="text-[11px] text-amber-700">Sélectionnez un client existant. Aucun client de démonstration n’est proposé.</p>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <label class="space-y-1.5"><span class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">{{ t('composer.starts_at') }} *</span><input type="date" :min="today" :value="modelValue.startsAt" class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface" data-test="starts-at-input" @input="update('startsAt', ($event.target as HTMLInputElement).value)" /></label>
      <label class="space-y-1.5"><span class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">{{ t('composer.ends_at') }} *</span><input type="date" :min="modelValue.startsAt || today" :value="modelValue.endsAt" class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface" data-test="ends-at-input" @input="update('endsAt', ($event.target as HTMLInputElement).value)" /></label>
    </div>

    <label class="block space-y-1.5"><span class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">{{ t('composer.project_name') }}</span><input type="text" :value="modelValue.projectName" class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface" @input="update('projectName', ($event.target as HTMLInputElement).value)" /></label>
    <label class="block space-y-1.5"><span class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">{{ t('composer.project_notes') }}</span><textarea :value="modelValue.notes" rows="3" class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface" @input="update('notes', ($event.target as HTMLTextAreaElement).value)" /></label>

    <div class="pt-3 border-t border-cortex-border flex justify-end"><button type="button" class="cx-btn-primary text-xs px-4 py-2 flex items-center gap-1.5" :disabled="!isStepValid" data-test="step1-next-btn" @click="emit('next')"><span>Suivant : Équipements & prix</span><ArrowRight class="w-3.5 h-3.5" /></button></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowRight } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { RentalCustomerOption } from '@/api/contracts/rentals'

const { t } = useI18n()
export interface ComposerStep1Data { customerId: string; customerName: string; customerEmail: string; startsAt: string; endsAt: string; projectName: string; notes: string }
const props = defineProps<{ modelValue: ComposerStep1Data }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: ComposerStep1Data): void; (e: 'next'): void }>()
const customerQuery = ref('')
const customers = ref<RentalCustomerOption[]>([])
const customersLoading = ref(false)
const selectedCustomer = computed(() => customers.value.find(c => c.id === props.modelValue.customerId))
const today = new Date().toISOString().slice(0, 10)
const isStepValid = computed(() => Boolean(props.modelValue.customerId && props.modelValue.startsAt && props.modelValue.endsAt && props.modelValue.endsAt > props.modelValue.startsAt))
let timer: ReturnType<typeof setTimeout> | undefined
watch(() => props.modelValue.customerName, value => { if (value && !customerQuery.value) customerQuery.value = value }, { immediate: true })
function update<K extends keyof ComposerStep1Data>(key: K, value: ComposerStep1Data[K]) { emit('update:modelValue', { ...props.modelValue, [key]: value }) }
function searchCustomers() {
  if (timer) clearTimeout(timer)
  if (customerQuery.value.trim().length < 2) { customers.value = []; return }
  timer = setTimeout(async () => {
    customersLoading.value = true
    try { customers.value = await getCortexApiClient().searchRentalCustomers(customerQuery.value.trim()) }
    catch { customers.value = [] }
    finally { customersLoading.value = false }
  }, 250)
}
function selectCustomer(customer: RentalCustomerOption) {
  customers.value = [customer, ...customers.value.filter(c => c.id !== customer.id)]
  emit('update:modelValue', { ...props.modelValue, customerId: customer.id, customerName: customer.name, customerEmail: '' })
  customerQuery.value = customer.name
}
</script>
