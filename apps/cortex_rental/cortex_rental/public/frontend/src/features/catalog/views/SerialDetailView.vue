<template>
  <div class="mx-auto max-w-3xl space-y-8" data-test="screen-serial-detail">
    <CortexPageHeader :title="String(route.params.serial)" :subtitle="data ? data.item_name : undefined" :provenance="data?.provenance">
      <template #actions>
        <RouterLink v-if="data" :to="`/app/cortex-equipment/${encodeURIComponent(data.item_code)}`" class="cx-btn-secondary inline-flex min-h-[40px] items-center px-4 text-sm">Voir l'équipement</RouterLink>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <CortexErrorBanner v-if="error" :error-message="error" @retry="reload" />
    <CortexSkeleton v-if="loading && !data" variant="rect" height="160px" />

    <dl v-if="data" class="grid gap-x-8 gap-y-4 sm:grid-cols-2">
      <div v-for="row in rows" :key="row.label">
        <dt class="text-sm text-cortex-text-secondary">{{ row.label }}</dt>
        <dd class="mt-1 text-base text-cortex-text-primary">{{ row.value }}</dd>
      </div>
    </dl>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getCortexApiClient } from '@/api'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'
import { SERIAL_LABELS } from '../serialLabels'

const route = useRoute()
const { data, loading, error, reload } = useResource(() => getCortexApiClient().getSerial({ serial_number: String(route.params.serial) }))
const NOT_PROVIDED = 'Non fourni'
const rows = computed(() => data.value ? [
  { label: 'État', value: SERIAL_LABELS[data.value.status] ?? data.value.status },
  { label: 'Entrepôt', value: data.value.warehouse ?? data.value.current_location ?? NOT_PROVIDED },
  { label: 'Consignation', value: data.value.is_consigned ? `Oui, propriétaire ${data.value.owner_name ?? data.value.owner_id ?? NOT_PROVIDED}` : 'Non' },
  { label: 'Part du propriétaire', value: data.value.consignment_rate != null ? `${data.value.consignment_rate} %` : NOT_PROVIDED },
  { label: 'Dernier entretien', value: data.value.last_maintenance_date ?? NOT_PROVIDED },
  { label: 'Prochain entretien', value: data.value.next_maintenance_date ?? NOT_PROVIDED }
] : [])
</script>
