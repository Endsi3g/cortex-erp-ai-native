<template>
  <div class="space-y-5" data-test="step-client-dates">
    <!-- Customer Selection -->
    <div class="space-y-1.5">
      <label class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
        {{ t('composer.client_label') }} *
      </label>
      <select
        :value="modelValue.customerId"
        class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:ring-1 focus:ring-cortex-primary-500"
        data-test="customer-select"
        @change="onCustomerChange(($event.target as HTMLSelectElement).value)"
      >
        <option value="" disabled>{{ t('composer.select_client') }}</option>
        <option
          v-for="cust in customers"
          :key="cust.id"
          :value="cust.id"
        >
          {{ cust.name }} ({{ cust.id }})
        </option>
      </select>
    </div>

    <!-- Customer Readiness Preview Banner -->
    <div
      v-if="selectedCustomer"
      class="p-4 rounded-xl border bg-cortex-surface shadow-2xs space-y-2.5"
      :class="isInsuranceExpired ? 'border-amber-400 bg-amber-50/30' : 'border-cortex-border'"
      data-test="customer-readiness-card"
    >
      <div class="flex items-center justify-between">
        <span class="text-xs font-bold text-cortex-text-primary">Profil Client & Readiness</span>
        <span
          class="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
          :class="selectedCustomer.account_status === 'Good' ? 'bg-cortex-primary-100 text-cortex-primary-800' : 'bg-amber-100 text-amber-800'"
        >
          Compte: {{ selectedCustomer.account_status }}
        </span>
      </div>

      <!-- Warning if insurance expired -->
      <div
        v-if="isInsuranceExpired"
        class="p-2.5 rounded-lg border border-red-300 bg-red-50 text-xs text-red-900 flex items-start gap-2"
        data-test="insurance-warning-banner"
      >
        <AlertTriangle class="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <strong class="font-bold">{{ t('composer.insurance_warning') }}</strong>
          <p class="text-[11px] mt-0.5">
            L'assurance a expiré le {{ selectedCustomer.insurance_valid_until }}. Une approbation de dérogation sera exigée pour confirmer le contrat.
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs pt-1">
        <div class="p-2 rounded bg-cortex-surface-secondary border border-cortex-border">
          <span class="text-[10px] text-cortex-text-muted block">Validité Assurance</span>
          <span class="font-mono font-semibold" :class="isInsuranceExpired ? 'text-red-600 font-bold' : 'text-cortex-text-primary'">
            {{ selectedCustomer.insurance_valid_until }}
          </span>
        </div>
        <div class="p-2 rounded bg-cortex-surface-secondary border border-cortex-border">
          <span class="text-[10px] text-cortex-text-muted block">Couverture Assurance</span>
          <span class="font-mono font-semibold text-cortex-text-primary">
            {{ formatCurrency(selectedCustomer.insurance_coverage_cad) }}
          </span>
        </div>
        <div class="p-2 rounded bg-cortex-surface-secondary border border-cortex-border">
          <span class="text-[10px] text-cortex-text-muted block">Caution au dossier</span>
          <span class="font-mono font-semibold text-cortex-text-primary">
            {{ formatCurrency(selectedCustomer.deposit_on_file_cad) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Dates Selection -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          {{ t('composer.starts_at') }} *
        </label>
        <input
          type="date"
          :value="modelValue.startsAt"
          class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:ring-1 focus:ring-cortex-primary-500 font-mono"
          data-test="starts-at-input"
          @input="emit('update:modelValue', { ...modelValue, startsAt: ($event.target as HTMLInputElement).value })"
        />
      </div>

      <div class="space-y-1.5">
        <label class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          {{ t('composer.ends_at') }} *
        </label>
        <input
          type="date"
          :value="modelValue.endsAt"
          class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:ring-1 focus:ring-cortex-primary-500 font-mono"
          data-test="ends-at-input"
          @input="emit('update:modelValue', { ...modelValue, endsAt: ($event.target as HTMLInputElement).value })"
        />
      </div>
    </div>

    <!-- Project Name & Operational Notes -->
    <div class="space-y-4">
      <div class="space-y-1.5">
        <label class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          {{ t('composer.project_name') }}
        </label>
        <input
          type="text"
          :value="modelValue.projectName"
          placeholder="ex: Tournage Long-Métrage — Hiver Laurentien"
          class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:ring-1 focus:ring-cortex-primary-500"
          data-test="project-name-input"
          @input="emit('update:modelValue', { ...modelValue, projectName: ($event.target as HTMLInputElement).value })"
        />
      </div>

      <div class="space-y-1.5">
        <label class="block text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          {{ t('composer.project_notes') }}
        </label>
        <textarea
          :value="modelValue.notes"
          rows="2"
          placeholder="Instructions spécifiques pour la préparation en entrepôt..."
          class="w-full text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:ring-1 focus:ring-cortex-primary-500"
          data-test="project-notes-input"
          @input="emit('update:modelValue', { ...modelValue, notes: ($event.target as HTMLTextAreaElement).value })"
        />
      </div>
    </div>

    <!-- Navigation Button -->
    <div class="pt-3 border-t border-cortex-border flex justify-end">
      <button
        type="button"
        class="cx-btn-primary text-xs px-4 py-2 flex items-center gap-1.5"
        :disabled="!isStepValid"
        data-test="step1-next-btn"
        @click="emit('next')"
      >
        <span>Suivant : Équipements & Prix</span>
        <ArrowRight class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, ArrowRight } from 'lucide-vue-next'
import { initialCustomers, type DemoCustomer } from '@/api/mock/fixtures/customers'

const { t } = useI18n()

export interface ComposerStep1Data {
  customerId: string
  customerName: string
  customerEmail: string
  startsAt: string
  endsAt: string
  projectName: string
  notes: string
}

const props = defineProps<{
  modelValue: ComposerStep1Data
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: ComposerStep1Data): void
  (e: 'next'): void
}>()

const customers = initialCustomers

const selectedCustomer = computed<DemoCustomer | undefined>(() => {
  return customers.find(c => c.id === props.modelValue.customerId)
})

const isInsuranceExpired = computed(() => {
  if (!selectedCustomer.value) return false
  const validUntil = new Date(selectedCustomer.value.insurance_valid_until)
  const today = new Date('2026-09-08')
  return validUntil < today
})

const isStepValid = computed(() => {
  return (
    props.modelValue.customerId !== '' &&
    props.modelValue.startsAt !== '' &&
    props.modelValue.endsAt !== ''
  )
})

const onCustomerChange = (id: string) => {
  const cust = customers.find(c => c.id === id)
  if (cust) {
    emit('update:modelValue', {
      ...props.modelValue,
      customerId: cust.id,
      customerName: cust.name,
      customerEmail: cust.contact_email
    })
  }
}

const formatCurrency = (amt: number) => {
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
}
</script>
