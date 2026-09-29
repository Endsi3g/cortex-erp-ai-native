<template>
  <div class="cx-page" data-test="screen-consignment-owners">
    <CortexPageHeader title="Propriétaires en consignation" subtitle="Versements en attente calculés depuis les versements enregistrés." :provenance="data?.provenance">
      <template #actions><RefreshButton :loading="loading" @refresh="reload" /></template>
    </CortexPageHeader>

    <form class="cx-filters" role="search" @submit.prevent="reload">
      <FilterField label="Rechercher un propriétaire"><input v-model="search" type="search" class="cx-field" placeholder="Nom ou code" /></FilterField>
    </form>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-if="loading && !data" class="cx-section"><CortexSkeleton variant="table-row" :count="5" /></div>
    <div v-else-if="data && !data.items.length" class="cx-empty"><strong>Aucun propriétaire</strong>Aucun propriétaire en consignation ne correspond.</div>
    <div v-else-if="data" class="cx-tablewrap">
      <table class="cx-table">
        <thead>
          <tr>
            <th scope="col" class="cx-rownum">#</th><th scope="col">Propriétaire</th><th scope="col">Contact</th>
            <th scope="col" class="num">Part par défaut</th><th scope="col" class="num">Séries actives</th><th scope="col" class="num">Versement en attente</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(owner, index) in data.items" :key="owner.id">
            <td class="cx-rownum">{{ index + 1 }}</td>
            <td>
              <RouterLink :to="`/app/cortex-owner-statement/${encodeURIComponent(owner.id)}/${period}`">{{ owner.display_name }}</RouterLink>
              <div class="font-mono text-xs" style="color: var(--erp-muted)">{{ owner.owner_code }}</div>
            </td>
            <td>{{ owner.contact_email || 'Non fourni' }}</td>
            <td class="num">{{ owner.default_commission_percentage }} %</td>
            <td class="num">{{ owner.active_serials_count }}</td>
            <td class="num">{{ formatCurrency(owner.pending_payout_amount) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getCortexApiClient } from '@/api'
import { formatCurrency } from '@/utils/currency'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import FilterField from '@/features/common/components/FilterField.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

const now = new Date()
const period = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
const search = ref('')
const { data, loading, error, reload } = useResource(() => getCortexApiClient().listOwners({ search: search.value || undefined, page: 1, page_size: 50 }))
</script>
