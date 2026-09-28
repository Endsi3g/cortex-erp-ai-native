<template>
  <div class="cx-page" data-test="screen-equipment-list">
    <CortexPageHeader title="Équipements" subtitle="Parc louable par profil. Les quantités viennent des numéros de série et des locations sorties." :provenance="data?.provenance">
      <template #actions><RefreshButton :loading="loading" @refresh="reload" /></template>
    </CortexPageHeader>

    <form class="cx-filters" role="search" @submit.prevent="reload">
      <FilterField label="Rechercher un équipement"><input v-model="search" type="search" class="cx-field" placeholder="Code ou nom" /></FilterField>
      <FilterField label="Catégorie">
        <select v-model="category" class="cx-field">
          <option value="">Catégorie</option>
          <option v-for="option in CATEGORIES" :key="option" :value="option">{{ option }}</option>
        </select>
      </FilterField>
    </form>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-if="loading && !data" class="cx-section"><CortexSkeleton variant="table-row" :count="6" /></div>
    <div v-else-if="data && !data.items.length" class="cx-empty"><strong>Aucun équipement trouvé</strong>Aucun profil de location ne correspond à ces critères.</div>
    <div v-else-if="data" class="cx-tablewrap">
      <table class="cx-table">
        <thead>
          <tr>
            <th scope="col" class="cx-rownum">#</th>
            <th scope="col">Équipement</th>
            <th scope="col">Catégorie</th>
            <th scope="col" class="num">Parc</th>
            <th scope="col" class="num">Disponible</th>
            <th scope="col" class="num">Sorti</th>
            <th scope="col" class="num">Maintenance</th>
            <th scope="col" class="num">Tarif / jour</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in data.items" :key="item.item_code">
            <td class="cx-rownum">{{ index + 1 }}</td>
            <td>
              <RouterLink :to="`/app/cortex-equipment/${encodeURIComponent(item.item_code)}`">{{ item.item_name }}</RouterLink>
              <div class="font-mono text-xs" style="color: var(--erp-muted)">{{ item.item_code }}</div>
            </td>
            <td>{{ item.category }}</td>
            <td class="num">{{ item.total_fleet_quantity }}</td>
            <td class="num">{{ item.available_quantity }}</td>
            <td class="num">{{ item.rented_quantity }}</td>
            <td class="num">{{ item.maintenance_quantity }}</td>
            <td class="num">{{ formatCurrency(item.daily_rate) }}</td>
          </tr>
        </tbody>
      </table>
      <p class="cx-caption">{{ data.items.length }} sur {{ data.total_count }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { getCortexApiClient } from '@/api'
import { formatCurrency } from '@/utils/currency'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import FilterField from '@/features/common/components/FilterField.vue'
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
