<template>
  <div data-test="tab-finance-pnl">
    <p class="cx-notice" style="margin: 0 0 16px">
      <span><strong>Règle tarifaire 7 jours = 3 jours.</strong> Pour {{ rental.calendar_days }} jours calendaires, {{ rental.billable_days }} jours sont facturés. Le serveur recalcule le prix et les taxes; ces montants viennent du devis.</span>
    </p>
    <h3 class="m-0 mb-3 text-base font-semibold">Facturation client</h3>
    <div class="cx-tablewrap" style="max-width: 640px">
      <table class="cx-table">
        <tbody>
          <tr><td>Sous-total des équipements</td><td class="num">{{ formatCurrency(rental.subtotal) }}</td></tr>
          <tr><td>Remises accordées</td><td class="num">{{ formatCurrency(rental.discount_total || 0) }}</td></tr>
          <tr><td>Taxes</td><td class="num">{{ formatCurrency(rental.tax_amount) }}</td></tr>
          <tr class="cx-total"><td>Total client</td><td class="num" data-test="finance-grand-total">{{ formatCurrency(rental.grand_total) }}</td></tr>
        </tbody>
      </table>
    </div>
    <p class="mt-4 mb-0 text-sm" style="color: var(--erp-muted)">
      La marge et la part des propriétaires en consignation ne sont pas calculées ici: elles dépendent des versements enregistrés.
      <RouterLink to="/app/cortex-consignment" style="color: var(--erp-accent)">Voir la consignation</RouterLink>.
    </p>
  </div>
</template>

<script setup lang="ts">
import type { RentalTransaction } from '@/types/rental'

defineProps<{ rental: RentalTransaction }>()

const formatCurrency = (amt: number) => new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
</script>
