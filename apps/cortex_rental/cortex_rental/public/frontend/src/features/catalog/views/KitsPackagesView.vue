<template>
  <div class="mx-auto max-w-5xl space-y-6" data-test="screen-kits">
    <CortexPageHeader title="Kits et forfaits" subtitle="Ensembles d'équipements définis comme « Product Bundle » dans ERPNext." :provenance="data?.provenance">
      <template #actions><RefreshButton :loading="loading" @refresh="reload" /></template>
    </CortexPageHeader>

    <CortexErrorBanner v-if="error" :error-message="error" @retry="reload" />
    <CortexSkeleton v-if="loading && !data" variant="table-row" :count="4" />
    <CortexEmptyState
      v-else-if="data && !data.kits.length"
      icon="archive"
      title="Aucun kit défini"
      description="Créez un Product Bundle pour un équipement de location afin de le voir ici."
    />
    <ul v-else-if="data" class="divide-y divide-cortex-border border-y border-cortex-border">
      <li v-for="kit in data.kits" :key="kit.kit_code" class="py-4">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h2 class="text-base font-semibold text-cortex-text-primary">{{ kit.kit_name }}</h2>
          <span class="text-sm text-cortex-text-secondary">{{ kit.category }} · <span class="font-mono">{{ kit.kit_code }}</span></span>
        </div>
        <ul class="mt-2 text-sm text-cortex-text-primary">
          <li v-for="component in kit.components" :key="component.item_code">{{ component.quantity }} × {{ component.item_name }}</li>
        </ul>
        <p class="mt-2 text-sm text-cortex-text-secondary">
          {{ kit.bundle_daily_rate != null ? `${formatCurrency(kit.bundle_daily_rate)} par jour` : 'Tarif du kit: non fourni par l’ERP.' }}
        </p>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { getCortexApiClient } from '@/api'
import { formatCurrency } from '@/utils/currency'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexEmptyState from '@/design-system/components/states/CortexEmptyState.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

const { data, loading, error, reload } = useResource(() => getCortexApiClient().listKits({}))
</script>
