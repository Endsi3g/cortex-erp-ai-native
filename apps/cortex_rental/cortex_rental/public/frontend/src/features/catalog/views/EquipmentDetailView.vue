<template>
  <div class="cx-page" data-test="screen-equipment-detail">
    <CortexPageHeader :title="data?.item_name ?? String(route.params.item)" :subtitle="data ? `${data.item_code} · ${data.category}` : undefined" :provenance="data?.provenance">
      <template #actions>
        <RouterLink to="/app/cortex-equipment" class="cx-btn-soft">Tous les équipements</RouterLink>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-if="loading && !data" class="cx-section"><CortexSkeleton variant="rect" height="120px" /></div>

    <template v-if="data">
      <KpiStrip :items="stats" />

      <div class="cx-two">
        <section class="cx-section" aria-labelledby="eq-price">
          <h2 id="eq-price">Tarification</h2>
          <p class="m-0 text-sm">{{ formatCurrency(data.daily_rate) }} par jour</p>
          <p class="mt-1 text-sm" style="color: var(--erp-muted)">Tarifs hebdomadaire et mensuel: non fournis par l'ERP. La règle 7 jours = 3 jours s'applique au devis.</p>
        </section>
        <section class="cx-section" aria-labelledby="eq-acc">
          <h2 id="eq-acc">Accessoires requis</h2>
          <ul v-if="data.required_accessories.length" class="m-0 list-disc pl-5 text-sm">
            <li v-for="accessory in data.required_accessories" :key="accessory">{{ accessory }}</li>
          </ul>
          <p v-else class="m-0 text-sm" style="color: var(--erp-muted)">Aucun accessoire requis déclaré.</p>
        </section>
      </div>

      <section class="cx-section" aria-labelledby="eq-serials">
        <h2 id="eq-serials">Numéros de série</h2>
        <p v-if="!data.is_serialized" class="m-0 text-sm" style="color: var(--erp-muted)">Cet équipement est suivi par quantité, sans numéro de série.</p>
        <p v-else-if="!(data.serials ?? []).length" class="m-0 text-sm" style="color: var(--erp-muted)">Aucun numéro de série enregistré.</p>
        <div v-else class="cx-tablewrap">
          <table class="cx-table">
            <thead><tr><th scope="col" class="cx-rownum">#</th><th scope="col">Numéro de série</th><th scope="col">État</th><th scope="col">Entrepôt</th></tr></thead>
            <tbody>
              <tr v-for="(serial, index) in data.serials" :key="serial.serial_number">
                <td class="cx-rownum">{{ index + 1 }}</td>
                <td><RouterLink :to="`/app/cortex-serial/${encodeURIComponent(serial.serial_number)}`" class="font-mono">{{ serial.serial_number }}</RouterLink></td>
                <td>{{ SERIAL_LABELS[serial.status] }}</td>
                <td>{{ serial.warehouse ?? 'Non fourni' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getCortexApiClient } from '@/api'
import { formatCurrency } from '@/utils/currency'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import KpiStrip, { type KpiItem } from '@/features/common/components/KpiStrip.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'
import { SERIAL_LABELS } from '../serialLabels'

const route = useRoute()
const { data, loading, error, reload } = useResource(() => getCortexApiClient().getEquipment({ item_code: String(route.params.item) }))
const stats = computed<KpiItem[]>(() => data.value ? [
  { key: 'fleet', label: 'Parc', value: String(data.value.total_fleet_quantity) },
  { key: 'available', label: 'Disponible', value: String(data.value.available_quantity), positive: true },
  { key: 'out', label: 'Sorti', value: String(data.value.rented_quantity) },
  { key: 'maintenance', label: 'Maintenance', value: String(data.value.maintenance_quantity) },
  { key: 'serialized', label: 'Sérialisé', value: data.value.is_serialized ? 'Oui' : 'Non' }
] : [])
</script>
