<template>
  <div data-test="tab-overview">
    <div class="cx-two" style="gap: 0 48px">
      <section aria-labelledby="ov-client">
        <h3 id="ov-client" class="m-0 mb-3 text-base font-semibold">Client et production</h3>
        <dl class="cx-dl">
          <div><dt>Société</dt><dd>{{ rental.customer_name }}</dd></div>
          <div><dt>Identifiant client</dt><dd class="font-mono">{{ rental.customer_id }}</dd></div>
          <div><dt>Courriel de contact</dt><dd>{{ rental.customer_contact_email || 'Non renseigné' }}</dd></div>
          <div><dt>Projet</dt><dd>{{ rental.project_name || 'Non renseigné' }}</dd></div>
        </dl>
      </section>
      <section aria-labelledby="ov-plan">
        <h3 id="ov-plan" class="m-0 mb-3 text-base font-semibold">Planning</h3>
        <dl class="cx-dl">
          <div><dt>Départ prévu</dt><dd>{{ rental.starts_at }}</dd></div>
          <div><dt>Retour prévu</dt><dd>{{ rental.ends_at }}</dd></div>
          <div><dt>Durée calendaire</dt><dd>{{ rental.calendar_days }} jours</dd></div>
          <div><dt>Jours facturés (règle 7 j = 3 j)</dt><dd>{{ rental.billable_days }} jours</dd></div>
        </dl>
      </section>
    </div>
    <section class="mt-6" aria-labelledby="ov-notes">
      <h3 id="ov-notes" class="m-0 mb-2 text-base font-semibold">Notes opérationnelles</h3>
      <p class="m-0 text-sm" style="color: var(--erp-text-2)">{{ rental.notes || 'Aucune note opérationnelle enregistrée.' }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { RentalTransaction } from '@/types/rental'

defineProps<{ rental: RentalTransaction }>()
</script>
