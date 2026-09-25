<template>
  <div class="space-y-4 text-xs" data-test="tab-overview">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Client & Contact Card -->
      <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-2.5">
        <h4 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px]">
          Coordonnées Client & Production
        </h4>
        <div class="space-y-1 text-cortex-text-secondary">
          <p><strong>Société :</strong> {{ rental.customer_name }}</p>
          <p><strong>ID Client :</strong> <span class="font-mono">{{ rental.customer_id }}</span></p>
          <p><strong>Courriel de contact :</strong> {{ rental.customer_contact_email || 'Non renseigné' }}</p>
          <p><strong>Projet :</strong> {{ rental.project_name || 'Non renseigné' }}</p>
        </div>
      </div>

      <!-- Dates & Dispatch Card -->
      <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-2.5">
        <h4 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px]">
          Planning & Logistique Entrepôt
        </h4>
        <div class="space-y-1 text-cortex-text-secondary">
          <p><strong>Départ prévu :</strong> <span class="font-mono">{{ rental.starts_at }}</span></p>
          <p><strong>Retour prévu :</strong> <span class="font-mono">{{ rental.ends_at }}</span></p>
          <p><strong>Durée calendaire :</strong> {{ rental.calendar_days }} jours</p>
          <p><strong>Jours facturés (règle 7j=3j) :</strong> <strong class="text-cortex-primary-700">{{ rental.billable_days }} jours</strong></p>
        </div>
      </div>
    </div>

    <!-- Notes Card -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-2">
      <h4 class="font-bold text-cortex-text-primary uppercase tracking-wider text-[11px]">
        Notes Opérationnelles
      </h4>
      <p class="text-cortex-text-secondary italic">
        {{ rental.notes || 'Aucune note opérationnelle enregistrée.' }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RentalTransaction } from '@/types/rental'

defineProps<{
  rental: RentalTransaction
}>()
</script>
