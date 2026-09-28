<template>
  <div class="mx-auto max-w-7xl space-y-6" data-test="screen-equipment-list">
    <CortexPageHeader
      title="Équipements"
      subtitle="Parc louable par profil. Les quantités viennent des numéros de série et des locations sorties."
      :provenance="data?.provenance"
    >
      <template #actions>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <form class="grid gap-4 sm:grid-cols-[minmax(0,20rem)_minmax(0,14rem)]" role="search" @submit.prevent="reload">
      <div>
        <label for="equipment-search" class="mb-1 block text-sm font-medium text-cortex-text-primary">Rechercher</label>
        <input id="equipment-search" v-model="search" type="search" placeholder="Code ou nom" class="min-h-[40px] w-full rounded-lg border border-cortex-border bg-cortex-surface px-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-cortex-primary-600" />
      </div>
      <div>
        <label for="equipment-category" class="mb-1 block text-sm font-medium text-cortex-text-primary">Catégorie</label>
        <select id="equipment-category" v-model="category" class="min-h-[40px] w-full rounded-lg border border-cortex-border bg-cortex-surface px-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-cortex-primary-600">
          <option value="">Toutes</option>
          <option v-for="option in CATEGORIES" :key="option" :value="option">{{ option }}</option>
        </select>
      </div>
    </form>

    <CortexErrorBanner v-if="error" :error-message="error" @retry="reload" />

    <CortexSkeleton v-if="loading && !data" variant="table-row" :count="6" />
    <CortexEmptyState
      v-else-if="data && !data.items.length"
      icon="archive"
      title="Aucun équipement trouvé"
      description="Aucun profil de location ne correspond à ces critères."
    />
    <div v-else-if="data" class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-cortex-border text-left text-cortex-text-secondary">
            <th scope="col" class="py-2 pr-4 font-medium">Équipement</th>
            <th scope="col" class="py-2 pr-4 font-medium">Catégorie</th>
            <th scope="col" class="py-2 pr-4 text-right font-medium">Parc</th>
            <th scope="col" class="py-2 pr-4 text-right font-medium">Disponible</th>
            <th scope="col" class="py-2 pr-4 text-right font-medium">Sorti</th>
            <th scope="col" class="py-2 pr-4 text-right font-medium">Maintenance</th>
            <th scope="col" class="py-2 text-right font-medium">Tarif / jour</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in data.items" :key="item.item_code" class="min-h-[48px] border-b border-cortex-border hover:bg-cortex-surface-subtle">
            <td class="py-3 pr-4">
              <RouterLink :to="`/app/cortex-equipment/${encodeURIComponent(item.item_code)}`" class="font-medium text-cortex-primary-700 underline">{{ item.item_name }}</RouterLink>
              <div class="font-mono text-xs text-cortex-text-secondary">{{ item.item_code }}</div>
            </td>
            <td class="py-3 pr-4">{{ item.category }}</td>
            <td class="py-3 pr-4 text-right tabular-nums">{{ item.total_fleet_quantity }}</td>
            <td class="py-3 pr-4 text-right tabular-nums">{{ item.available_quantity }}</td>
            <td class="py-3 pr-4 text-right tabular-nums">{{ item.rented_quantity }}</td>
            <td class="py-3 pr-4 text-right tabular-nums">{{ item.maintenance_quantity }}</td>
            <td class="py-3 text-right tabular-nums">{{ formatCurrency(item.daily_rate) }}</td>
          </tr>
        </tbody>
      </table>
      <p class="mt-3 text-sm text-cortex-text-secondary">{{ data.items.length }} sur {{ data.total_count }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { getCortexApiClient } from '@/api'
import { formatCurrency } from '@/utils/currency'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexEmptyState from '@/design-system/components/states/CortexEmptyState.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

// Options of Cortex Rental Item Profile.category.
const CATEGORIES = ['Camera Bodies', 'Cinema Lenses', 'Lighting', 'Grip & Rigging', 'Audio', 'Monitors & Wireless Video', 'Power & Batteries']

const search = ref('')
const category = ref('')
const { data, loading, error, reload } = useResource(() =>
  getCortexApiClient().listEquipment({ search: search.value || undefined, category: category.value || undefined, page: 1, page_size: 50 })
)
watch(category, reload)
</script>
