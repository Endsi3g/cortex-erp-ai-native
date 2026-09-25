<template>
  <div
    class="p-4 rounded-xl border bg-cortex-surface shadow-2xs space-y-3"
    :class="readiness.overall_ready ? 'border-cortex-border' : 'border-amber-300 bg-amber-50/20'"
    data-test="rental-readiness-card"
  >
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <ShieldCheck class="w-4 h-4 text-cortex-primary-600" />
        <h3 class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          {{ t('rental_detail.readiness_title') }}
        </h3>
      </div>
      <span
        class="px-2 py-0.5 rounded text-[10px] font-bold"
        :class="readiness.overall_ready ? 'bg-cortex-primary-100 text-cortex-primary-800' : 'bg-amber-100 text-amber-900'"
      >
        {{ readiness.overall_ready ? '✓ Prêt pour Sortie' : '⚠ Pré-requis Incomplets' }}
      </span>
    </div>

    <!-- 3 Checks -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
      <!-- Account -->
      <div class="p-2.5 rounded-lg border border-cortex-border bg-cortex-surface flex items-center justify-between">
        <span class="text-cortex-text-secondary">{{ t('rental_detail.readiness_account') }}</span>
        <span
          class="font-bold flex items-center gap-1"
          :class="readiness.customer_account_ready ? 'text-cortex-primary-700' : 'text-amber-600'"
        >
          {{ readiness.customer_account_ready ? '✓ Validé' : '⚠ À réviser' }}
        </span>
      </div>

      <!-- Insurance -->
      <div class="p-2.5 rounded-lg border border-cortex-border bg-cortex-surface flex items-center justify-between">
        <span class="text-cortex-text-secondary">{{ t('rental_detail.readiness_insurance') }}</span>
        <span
          class="font-bold flex items-center gap-1"
          :class="readiness.insurance_ready ? 'text-cortex-primary-700' : 'text-red-600'"
        >
          {{ readiness.insurance_ready ? '✓ Conforme' : '✗ Non conforme' }}
        </span>
      </div>

      <!-- Payment -->
      <div class="p-2.5 rounded-lg border border-cortex-border bg-cortex-surface flex items-center justify-between">
        <span class="text-cortex-text-secondary">{{ t('rental_detail.readiness_payment') }}</span>
        <span
          class="font-bold flex items-center gap-1"
          :class="readiness.payment_ready ? 'text-cortex-primary-700' : 'text-amber-600'"
        >
          {{ readiness.payment_ready ? '✓ Caution active' : '⚠ Caution requise' }}
        </span>
      </div>
    </div>

    <!-- Missing Requirements Warning Banner -->
    <div
      v-if="readiness.missing_requirements && readiness.missing_requirements.length > 0"
      class="p-2.5 rounded-lg border border-amber-300 bg-amber-50 text-xs text-amber-900 space-y-1"
      data-test="missing-requirements-banner"
    >
      <div class="flex items-center gap-1.5 font-bold">
        <AlertTriangle class="w-3.5 h-3.5 text-amber-700" />
        <span>Conditions bloquantes avant confirmation contrat :</span>
      </div>
      <ul class="list-disc list-inside text-[11px] space-y-0.5 pl-1">
        <li v-for="req in readiness.missing_requirements" :key="req">
          {{ req }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ShieldCheck, AlertTriangle } from 'lucide-vue-next'
import type { RentalReadiness } from '@/types/rental'

const { t } = useI18n()

defineProps<{
  readiness: RentalReadiness
}>()
</script>
