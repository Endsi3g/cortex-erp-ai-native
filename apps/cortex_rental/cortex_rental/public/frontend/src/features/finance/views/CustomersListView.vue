<template>
  <div class="cx-page" data-test="screen-customers">
    <CortexPageHeader title="Clients" subtitle="Clients ERPNext avec l'activité de location comptée sur les transactions." :provenance="data?.provenance">
      <template #actions>
        <a class="cx-btn-secondary" href="/app/customer">Liste ERPNext</a>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <form class="cx-filters" role="search" @submit.prevent="reload">
      <FilterField label="Rechercher un client"><input v-model="search" type="search" class="cx-field" placeholder="Nom ou identifiant" /></FilterField>
    </form>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-else-if="loading && !data" class="cx-section"><CortexSkeleton variant="table-row" :count="5" /></div>
    <div v-else-if="data && !data.items.length" class="cx-empty"><strong>Aucun client</strong>Aucun client ne correspond à cette recherche.</div>
    <div v-else-if="data" class="cx-tablewrap">
      <table class="cx-table">
        <thead>
          <tr>
            <th scope="col" class="cx-rownum">#</th><th scope="col">Client</th><th scope="col">Groupe</th>
            <th scope="col" class="num">Locations</th><th scope="col" class="num">En cours</th><th scope="col" class="num">Facturé (TTC)</th><th scope="col">Dernier départ</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(customer, index) in data.items" :key="customer.id">
            <td class="cx-rownum">{{ index + 1 }}</td>
            <td>
              <a :href="`/app/customer/${encodeURIComponent(customer.id)}`">{{ customer.name }}</a>
              <div class="font-mono text-xs" style="color: var(--erp-muted)">{{ customer.id }}</div>
            </td>
            <td>{{ customer.customer_group || '—' }}</td>
            <td class="num">{{ customer.rentals_count }}</td>
            <td class="num">{{ customer.open_rentals_count }}</td>
            <td class="num">{{ formatCurrency(customer.billed_total) }}</td>
            <td>{{ customer.last_rental_start ? formatDate(customer.last_rental_start) : '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getCortexApiClient } from '@/api'
import { formatDate } from '@/app/i18n/formatters'
import { formatCurrency } from '@/utils/currency'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import FilterField from '@/features/common/components/FilterField.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

const search = ref('')
const { data, loading, error, reload } = useResource(() => getCortexApiClient().listCustomers({ search: search.value || undefined, page: 1, page_size: 50 }))
</script>
