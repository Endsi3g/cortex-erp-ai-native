<template>
  <div class="mx-auto max-w-5xl space-y-8" data-test="screen-equipment-detail">
    <CortexPageHeader :title="data?.item_name ?? String(route.params.item)" :subtitle="data ? `${data.item_code} · ${data.category}` : undefined" :provenance="data?.provenance">
      <template #actions>
        <RouterLink to="/app/cortex-equipment" class="cx-btn-secondary inline-flex min-h-[40px] items-center px-4 text-sm">Tous les équipements</RouterLink>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <CortexErrorBanner v-if="error" :error-message="error" @retry="reload" />
    <CortexSkeleton v-if="loading && !data" variant="rect" height="160px" />

    <template v-if="data">
      <dl class="grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-5">
        <div v-for="stat in stats" :key="stat.label">
          <dt class="text-sm text-cortex-text-secondary">{{ stat.label }}</dt>
          <dd class="mt-1 text-2xl font-semibold tabular-nums text-cortex-text-primary">{{ stat.value }}</dd>
        </div>
      </dl>

      <section aria-labelledby="eq-info" class="grid gap-6 sm:grid-cols-2">
        <div>
          <h2 id="eq-info" class="mb-2 text-lg font-semibold text-cortex-text-primary">Tarification</h2>
          <p class="text-sm text-cortex-text-primary">{{ formatCurrency(data.daily_rate) }} par jour</p>
          <p class="mt-1 text-sm text-cortex-text-secondary">Tarifs hebdomadaire et mensuel: non fournis par l'ERP. La règle 7 jours = 3 jours s'applique au devis.</p>
        </div>
        <div>
          <h2 class="mb-2 text-lg font-semibold text-cortex-text-primary">Accessoires requis</h2>
          <ul v-if="data.required_accessories.length" class="list-disc pl-5 text-sm text-cortex-text-primary">
            <li v-for="accessory in data.required_accessories" :key="accessory">{{ accessory }}</li>
          </ul>
          <p v-else class="text-sm text-cortex-text-secondary">Aucun accessoire requis déclaré.</p>
        </div>
      </section>

      <section aria-labelledby="eq-serials">
        <h2 id="eq-serials" class="mb-2 text-lg font-semibold text-cortex-text-primary">Numéros de série</h2>
        <p v-if="!data.is_serialized" class="text-sm text-cortex-text-secondary">Cet équipement est suivi par quantité, sans numéro de série.</p>
        <p v-else-if="!(data.serials ?? []).length" class="text-sm text-cortex-text-secondary">Aucun numéro de série enregistré.</p>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b border-cortex-border text-left text-cortex-text-secondary">
              <th scope="col" class="py-2 pr-4 font-medium">Numéro de série</th>
              <th scope="col" class="py-2 pr-4 font-medium">État</th>
              <th scope="col" class="py-2 font-medium">Entrepôt</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="serial in data.serials" :key="serial.serial_number" class="min-h-[48px] border-b border-cortex-border">
              <td class="py-3 pr-4"><RouterLink :to="`/app/cortex-serial/${encodeURIComponent(serial.serial_number)}`" class="font-mono text-cortex-primary-700 underline">{{ serial.serial_number }}</RouterLink></td>
              <td class="py-3 pr-4">{{ SERIAL_LABELS[serial.status] }}</td>
              <td class="py-3">{{ serial.warehouse ?? 'Non fourni' }}</td>
            </tr>
          </tbody>
        </table>
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
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'
import { SERIAL_LABELS } from '../serialLabels'

const route = useRoute()
const { data, loading, error, reload } = useResource(() => getCortexApiClient().getEquipment({ item_code: String(route.params.item) }))
const stats = computed(() => data.value ? [
  { label: 'Parc', value: data.value.total_fleet_quantity },
  { label: 'Disponible', value: data.value.available_quantity },
  { label: 'Sorti', value: data.value.rented_quantity },
  { label: 'Maintenance', value: data.value.maintenance_quantity },
  { label: 'Sérialisé', value: data.value.is_serialized ? 'Oui' : 'Non' }
] : [])
</script>
