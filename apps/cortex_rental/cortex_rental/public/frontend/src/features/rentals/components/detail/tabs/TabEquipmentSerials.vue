<template>
  <div class="rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs overflow-hidden" data-test="tab-equipment-serials">
    <div class="p-4 border-b border-cortex-border flex items-center justify-between">
      <h3 class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
        Équipements & Séries Assignées ({{ rental.items.length }} lignes)
      </h3>
      <span class="text-xs text-cortex-text-muted">
        Règle 7j=3j appliquée
      </span>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-xs text-left">
        <thead class="bg-cortex-surface-secondary text-cortex-text-muted text-[10px] font-bold uppercase tracking-wider border-b border-cortex-border">
          <tr>
            <th class="px-4 py-2.5">Équipement</th>
            <th class="px-4 py-2.5">Catégorie</th>
            <th class="px-4 py-2.5 text-center">Qté</th>
            <th class="px-4 py-2.5">Numéros de Série Assignés</th>
            <th class="px-4 py-2.5">Statut Consignation</th>
            <th class="px-4 py-2.5 text-right">Tarif / j</th>
            <th class="px-4 py-2.5 text-right">Sous-total ({{ rental.billable_days }}j)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-cortex-border">
          <tr
            v-for="item in rental.items"
            :key="item.id"
            class="hover:bg-cortex-bg-secondary/30 transition-colors"
            :data-test="`detail-line-${item.item_code}`"
          >
            <!-- Equipment -->
            <td class="px-4 py-3">
              <span class="font-semibold text-cortex-text-primary block">{{ item.item_name }}</span>
              <span class="font-mono text-[10px] text-cortex-primary-700 bg-cortex-primary-50 px-1 rounded">
                {{ item.item_code }}
              </span>
            </td>

            <!-- Category -->
            <td class="px-4 py-3 text-cortex-text-secondary">
              {{ item.category }}
            </td>

            <!-- Quantity -->
            <td class="px-4 py-3 text-center font-mono font-semibold">
              {{ item.quantity }}
            </td>

            <!-- Assigned Serials Chips -->
            <td class="px-4 py-3">
              <div v-if="item.assigned_serials && item.assigned_serials.length > 0" class="flex flex-wrap gap-1">
                <span
                  v-for="sn in item.assigned_serials"
                  :key="sn"
                  class="px-2 py-0.5 rounded font-mono text-[11px] font-semibold border flex items-center gap-1"
                  :class="getSerialStatusClass(item, sn)"
                >
                  <span>{{ sn }}</span>
                  <span v-if="item.scanned_checkin_serials.includes(sn)" class="text-[9px] text-cortex-primary-700 font-bold">✓ In</span>
                  <span v-else-if="item.scanned_checkout_serials.includes(sn)" class="text-[9px] text-purple-700 font-bold">● Out</span>
                </span>
              </div>
              <span v-else class="text-cortex-text-muted italic">
                Non sérialisé / en vrac
              </span>
            </td>

            <!-- Consignment -->
            <td class="px-4 py-3">
              <span
                v-if="item.is_consigned"
                class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300"
                data-test="consignment-badge"
              >
                Consigné ({{ item.owner_code }})
              </span>
              <span v-else class="text-cortex-text-muted text-[11px]">
                Flotte interne
              </span>
            </td>

            <!-- Rate -->
            <td class="px-4 py-3 text-right font-mono text-cortex-text-secondary">
              {{ formatCurrency(item.daily_rate) }}
            </td>

            <!-- Subtotal -->
            <td class="px-4 py-3 text-right font-mono font-bold text-cortex-text-primary">
              {{ formatCurrency(item.subtotal) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RentalTransaction, RentalLineItem } from '@/types/rental'

defineProps<{
  rental: RentalTransaction
}>()

const getSerialStatusClass = (item: RentalLineItem, sn: string) => {
  if (item.scanned_checkin_serials.includes(sn)) {
    return 'bg-cortex-primary-50 text-cortex-primary-900 border-cortex-primary-300'
  }
  if (item.scanned_checkout_serials.includes(sn)) {
    return 'bg-purple-50 text-purple-900 border-purple-300'
  }
  return 'bg-cortex-surface-secondary text-cortex-text-primary border-cortex-border'
}

const formatCurrency = (amt: number) => {
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
}
</script>
