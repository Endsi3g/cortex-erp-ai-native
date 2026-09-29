<template>
  <section class="cx-section" aria-label="Résumé de la location" data-test="rental-header-banner">
    <dl class="cx-dl">
      <div><dt>Statut</dt><dd><CortexBadge :variant="mapStateToBadge(rental.rental_state)" size="sm" /></dd></div>
      <div><dt>Client</dt><dd>{{ rental.customer_name }}</dd></div>
      <div v-if="rental.project_name"><dt>Projet</dt><dd>{{ rental.project_name }}</dd></div>
      <div><dt>Période</dt><dd>{{ formatDateRange(rental.starts_at, rental.ends_at) }}</dd></div>
      <div><dt>Jours facturés / calendaires</dt><dd>{{ rental.billable_days }} / {{ rental.calendar_days }}</dd></div>
      <div><dt>Total taxes incluses</dt><dd data-test="header-grand-total">{{ formatCurrency(rental.grand_total) }}</dd></div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import type { RentalTransaction, RentalState } from '@/types/rental'
import CortexBadge from '@/design-system/components/base/CortexBadge.vue'

defineProps<{ rental: RentalTransaction }>()

const mapStateToBadge = (state: RentalState) => {
  switch (state) {
    case 'Quote': return 'quote'
    case 'Reservation': return 'reservation'
    case 'Contract': return 'contract'
    case 'Checked Out': return 'checked_out'
    case 'Partially Returned': return 'partial_return'
    case 'Returned': return 'returned'
    case 'Invoiced': return 'invoiced'
    case 'Cancelled': return 'cancelled'
    default: return 'draft'
  }
}

const formatDateRange = (startsAt: string, endsAt: string) => {
  try {
    const s = new Date(startsAt)
    const e = new Date(endsAt)
    return `${s.getDate()}/${s.getMonth() + 1} → ${e.getDate()}/${e.getMonth() + 1}/${e.getFullYear()}`
  } catch {
    return `${startsAt} → ${endsAt}`
  }
}

const formatCurrency = (amt: number) => new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
</script>
