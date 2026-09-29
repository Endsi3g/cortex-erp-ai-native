<template>
  <div data-test="tab-equipment-serials">
    <h3 class="m-0 mb-3 text-base font-semibold">Équipements et séries assignées ({{ rental.items.length }} lignes)</h3>
    <div class="cx-tablewrap">
      <table class="cx-table">
        <thead>
          <tr>
            <th scope="col" class="cx-rownum">#</th><th scope="col">Équipement</th><th scope="col">Catégorie</th><th scope="col" class="num">Qté</th>
            <th scope="col">Numéros de série</th><th scope="col">Consignation</th><th scope="col" class="num">Tarif / jour</th>
            <th scope="col" class="num">Sous-total ({{ rental.billable_days }} j)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in rental.items" :key="item.id" :data-test="`detail-line-${item.item_code}`">
            <td class="cx-rownum">{{ index + 1 }}</td>
            <td>{{ item.item_name }}<div class="font-mono text-xs" style="color: var(--erp-muted)">{{ item.item_code }}</div></td>
            <td>{{ item.category }}</td>
            <td class="num">{{ item.quantity }}</td>
            <td class="wrap">
              <template v-if="item.assigned_serials && item.assigned_serials.length > 0">
                <span v-for="sn in item.assigned_serials" :key="sn" class="cx-tag mr-1" :class="item.scanned_checkin_serials.includes(sn) ? 'cx-tag--ok' : ''">
                  <span class="font-mono">{{ sn }}</span>
                  <span v-if="item.scanned_checkin_serials.includes(sn)">&nbsp;· retourné</span>
                  <span v-else-if="item.scanned_checkout_serials.includes(sn)">&nbsp;· sorti</span>
                </span>
              </template>
              <span v-else style="color: var(--erp-muted)">Non sérialisé</span>
            </td>
            <td>
              <span v-if="item.is_consigned" class="cx-tag cx-tag--warn" data-test="consignment-badge">Consigné ({{ item.owner_code }})</span>
              <span v-else style="color: var(--erp-muted)">Flotte interne</span>
            </td>
            <td class="num">{{ formatCurrency(item.daily_rate) }}</td>
            <td class="num">{{ formatCurrency(item.subtotal) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RentalTransaction } from '@/types/rental'

defineProps<{ rental: RentalTransaction }>()

const formatCurrency = (amt: number) => new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
</script>
