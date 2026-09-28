<template>
  <section class="cx-section" aria-labelledby="readiness-title" data-test="rental-readiness-card">
    <h2 id="readiness-title">{{ t('rental_detail.readiness_title') }}</h2>
    <dl class="cx-dl">
      <div><dt>{{ t('rental_detail.readiness_account') }}</dt><dd>{{ readiness.customer_account_ready ? '✓ Validé' : '⚠ À réviser' }}</dd></div>
      <div><dt>{{ t('rental_detail.readiness_insurance') }}</dt><dd>{{ readiness.insurance_ready ? '✓ Conforme' : '✗ Non conforme' }}</dd></div>
      <div><dt>{{ t('rental_detail.readiness_payment') }}</dt><dd>{{ readiness.payment_ready ? '✓ Caution active' : '⚠ Caution requise' }}</dd></div>
      <div><dt>Sortie</dt><dd>{{ readiness.overall_ready ? '✓ Prêt pour la sortie' : '⚠ Pré-requis incomplets' }}</dd></div>
    </dl>
    <div v-if="readiness.missing_requirements && readiness.missing_requirements.length > 0" class="cx-notice" style="margin: 12px 0 0" data-test="missing-requirements-banner">
      <div>
        <strong>Conditions bloquantes avant confirmation du contrat</strong>
        <ul class="m-0 mt-1 list-disc pl-5">
          <li v-for="req in readiness.missing_requirements" :key="req">{{ req }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { RentalReadiness } from '@/types/rental'

const { t } = useI18n()

defineProps<{ readiness: RentalReadiness }>()
</script>
