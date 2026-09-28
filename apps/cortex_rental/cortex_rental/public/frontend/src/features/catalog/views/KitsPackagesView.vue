<template>
  <div class="cx-page" data-test="screen-kits">
    <CortexPageHeader title="Kits et forfaits" subtitle="Ensembles d'équipements définis comme « Product Bundle » dans ERPNext." :provenance="data?.provenance">
      <template #actions><RefreshButton :loading="loading" @refresh="reload" /></template>
    </CortexPageHeader>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-if="loading && !data" class="cx-section"><CortexSkeleton variant="table-row" :count="4" /></div>
    <div v-else-if="data && !data.kits.length" class="cx-empty"><strong>Aucun kit défini</strong>Créez un Product Bundle pour un équipement de location afin de le voir ici.</div>
    <div v-else-if="data" class="cx-tablewrap">
      <table class="cx-table">
        <thead>
          <tr><th scope="col" class="cx-rownum">#</th><th scope="col">Kit</th><th scope="col">Catégorie</th><th scope="col">Composants</th><th scope="col" class="num">Tarif / jour</th></tr>
        </thead>
        <tbody>
          <tr v-for="(kit, index) in data.kits" :key="kit.kit_code">
            <td class="cx-rownum">{{ index + 1 }}</td>
            <td><strong>{{ kit.kit_name }}</strong><div class="font-mono text-xs" style="color: var(--erp-muted)">{{ kit.kit_code }}</div></td>
            <td>{{ kit.category }}</td>
            <td>{{ kit.components.map((c) => `${c.quantity} × ${c.item_name}`).join(', ') }}</td>
            <td class="num">{{ kit.bundle_daily_rate != null ? formatCurrency(kit.bundle_daily_rate) : 'Non fourni' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getCortexApiClient } from '@/api'
import { formatCurrency } from '@/utils/currency'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

const { data, loading, error, reload } = useResource(() => getCortexApiClient().listKits({}))
</script>
