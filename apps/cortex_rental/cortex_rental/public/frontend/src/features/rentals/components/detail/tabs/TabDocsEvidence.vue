<template>
  <div data-test="tab-docs-evidence">
    <h3 class="m-0 mb-3 text-base font-semibold">Documents et preuves</h3>
    <p class="cx-notice" style="margin: 0" role="status" data-test="upload-evidence-simulator">
      Les documents contractuels, les certificats d'assurance et le téléversement de preuves ne sont pas encore exposés par un endpoint Cortex.
      Les pièces jointes de cette location restent consultables dans la fiche de la location.
    </p>
    <p class="mt-4 mb-0">
      <a :href="`/app/cortex-rental-transaction/${encodeURIComponent(rental.name)}`" class="cx-btn-soft">Ouvrir la fiche de la location</a>
    </p>
  </div>
</template>

<script setup lang="ts">
import type { RentalTransaction } from '@/types/rental'

defineProps<{ rental: RentalTransaction }>()
</script>
