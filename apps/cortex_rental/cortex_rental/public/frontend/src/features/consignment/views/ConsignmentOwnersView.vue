<template>
  <div class="mx-auto max-w-7xl space-y-6" data-test="screen-consignment-owners">
    <CortexPageHeader title="Propriétaires en consignation" subtitle="Versements en attente calculés depuis les versements enregistrés." :provenance="data?.provenance">
      <template #actions><RefreshButton :loading="loading" @refresh="reload" /></template>
    </CortexPageHeader>

    <form role="search" class="max-w-xs" @submit.prevent="reload">
      <label for="owner-search" class="mb-1 block text-sm font-medium text-cortex-text-primary">Rechercher</label>
      <input id="owner-search" v-model="search" type="search" placeholder="Nom ou code" class="min-h-[40px] w-full rounded-lg border border-cortex-border bg-cortex-surface px-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-cortex-primary-600" />
    </form>

    <CortexErrorBanner v-if="error" :error-message="error" @retry="reload" />
    <CortexSkeleton v-if="loading && !data" variant="table-row" :count="5" />
    <CortexEmptyState v-else-if="data && !data.items.length" icon="archive" title="Aucun propriétaire" description="Aucun propriétaire en consignation ne correspond." />
    <div v-else-if="data" class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-cortex-border text-left text-cortex-text-secondary">
            <th scope="col" class="py-2 pr-4 font-medium">Propriétaire</th>
            <th scope="col" class="py-2 pr-4 font-medium">Contact</th>
            <th scope="col" class="py-2 pr-4 text-right font-medium">Part par défaut</th>
            <th scope="col" class="py-2 pr-4 text-right font-medium">Séries actives</th>
            <th scope="col" class="py-2 text-right font-medium">Versement en attente</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="owner in data.items" :key="owner.id" class="min-h-[48px] border-b border-cortex-border">
            <td class="py-3 pr-4">
              <RouterLink :to="`/app/cortex-owner-statement/${encodeURIComponent(owner.id)}/${period}`" class="font-medium text-cortex-primary-700 underline">{{ owner.display_name }}</RouterLink>
              <div class="font-mono text-xs text-cortex-text-secondary">{{ owner.owner_code }}</div>
            </td>
            <td class="py-3 pr-4">{{ owner.contact_email || 'Non fourni' }}</td>
            <td class="py-3 pr-4 text-right tabular-nums">{{ owner.default_commission_percentage }} %</td>
            <td class="py-3 pr-4 text-right tabular-nums">{{ owner.active_serials_count }}</td>
            <td class="py-3 text-right tabular-nums">{{ formatCurrency(owner.pending_payout_amount) }}</td>
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
import CortexEmptyState from '@/design-system/components/states/CortexEmptyState.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

const now = new Date()
const period = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
const search = ref('')
const { data, loading, error, reload } = useResource(() => getCortexApiClient().listOwners({ search: search.value || undefined, page: 1, page_size: 50 }))
</script>
