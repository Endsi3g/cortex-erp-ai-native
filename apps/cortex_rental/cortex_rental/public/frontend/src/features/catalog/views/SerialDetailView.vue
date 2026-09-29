<template>
  <div class="cx-page" data-test="screen-serial-detail">
    <CortexPageHeader :title="String(route.params.serial)" :subtitle="data ? data.item_name : undefined" :provenance="data?.provenance">
      <template #actions>
        <RouterLink v-if="data" :to="`/app/cortex-equipment/${encodeURIComponent(data.item_code)}`" class="cx-btn-soft">Voir l'équipement</RouterLink>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-if="loading && !data" class="cx-section"><CortexSkeleton variant="rect" height="120px" /></div>

    <section v-if="data" class="cx-section" aria-label="Détails du numéro de série">
      <dl class="cx-dl">
        <div v-for="row in rows" :key="row.label"><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></div>
      </dl>
    </section>
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
