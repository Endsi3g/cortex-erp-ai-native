<template>
  <div class="cx-page" data-test="screen-owner-statement">
    <CortexPageHeader :title="statement ? `Relevé — ${statement.owner.display_name}` : 'Relevé propriétaire'" subtitle="Décompte de consignation sans donnée locataire.">
      <template #actions>
        <RouterLink to="/app/cortex-consignment" class="cx-btn-soft">Consignation</RouterLink>
        <button v-if="statement" type="button" class="cx-btn-soft" :disabled="isExporting" @click="handleExport('csv')">Exporter CSV</button>
        <button v-if="statement" type="button" class="cx-btn-soft" :disabled="isExporting" @click="handleExport('pdf')">Exporter PDF</button>
        <RefreshButton :loading="isLoading" @refresh="loadStatement" />
      </template>
    </CortexPageHeader>

    <div class="cx-notice" role="note" data-test="privacy-banner">
      <span><strong>Confidentialité:</strong> informations clients exclues, seules les données de l'équipement et du versement figurent sur ce relevé.</span>
    </div>
    <div v-if="exportMessage" class="cx-notice" role="status">
      <span>{{ exportMessage }}</span>
      <button type="button" class="cx-btn-soft" @click="exportMessage = ''">Fermer</button>
    </div>

    <div v-if="errorMessage" class="cx-section"><CortexErrorBanner :error-message="errorMessage" @retry="loadStatement" /></div>
    <div v-if="isLoading && !statement" class="cx-section"><CortexSkeleton variant="table-row" :count="4" /></div>

    <template v-if="statement">
      <section class="cx-section" aria-label="Identification du relevé">
        <dl class="cx-dl">
          <div><dt>Propriétaire</dt><dd>{{ statement.owner.display_name }}</dd></div>
          <div><dt>Code</dt><dd class="font-mono">{{ statement.owner.code }}</dd></div>
          <div><dt>Période</dt><dd>{{ statement.period.start }} au {{ statement.period.end }}</dd></div>
          <div><dt>Généré le</dt><dd>{{ formatDate(statement.generated_at) }}</dd></div>
        </dl>
      </section>

      <KpiStrip :items="kpis" />

      <section class="cx-section" aria-labelledby="stmt-lines">
        <h2 id="stmt-lines">Détail par équipement ({{ statement.lines.length }})</h2>
        <div v-if="!statement.lines.length" class="cx-empty"><strong>Aucun versement</strong>Aucun versement n'est enregistré pour ce propriétaire sur cette période.</div>
        <div v-else class="cx-tablewrap">
          <table class="cx-table">
            <thead>
              <tr>
                <th scope="col" class="cx-rownum">#</th><th scope="col">Équipement</th><th scope="col">Numéro de série</th>
                <th scope="col" class="num">Jours facturés</th><th scope="col" class="num">Taux journalier</th>
                <th scope="col" class="num">Remise</th><th scope="col" class="num">Part</th><th scope="col" class="num">Montant propriétaire</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(line, index) in statement.lines" :key="`${line.serial_number}_${index}`">
                <td class="cx-rownum">{{ index + 1 }}</td>
                <td>{{ line.equipment_name }}</td>
                <td class="font-mono">{{ line.serial_number }}</td>
                <td class="num">{{ line.billable_days }}</td>
                <td class="num">{{ formatMoney(line.rate) }}</td>
                <td class="num">{{ formatMoney(line.discount_amount) }}</td>
                <td class="num">{{ line.consignment_percentage }} %</td>
                <td class="num">{{ formatMoney(line.owner_amount) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="cx-caption" style="padding-left: 0">Version du relevé: {{ statement.snapshot_version }}</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getCortexApiClient } from '@/api'
import type { OwnerStatementSafe } from '@/api/contracts'
import { formatCurrency } from '@/utils/formatters'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import KpiStrip, { type KpiItem } from '@/features/common/components/KpiStrip.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'

const route = useRoute()

const ownerId = computed(() => String(route.params.owner || ''))
const period = computed(() => String(route.params.period || ''))

const statement = ref<OwnerStatementSafe | null>(null)
const isLoading = ref(true)
const errorMessage = ref('')
const isExporting = ref(false)
const exportMessage = ref('')

async function loadStatement() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const client = getCortexApiClient()
    const res = await client.getOwnerStatement({
      owner_id: ownerId.value,
      period: period.value
    })
    statement.value = res.statement
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Impossible de générer le relevé propriétaire.'
  } finally {
    isLoading.value = false
  }
}

async function handleExport(format: 'pdf' | 'csv') {
  if (!statement.value) return
  isExporting.value = true
  exportMessage.value = ''

  try {
    const client = getCortexApiClient()
    const res = await client.requestOwnerStatementExport({
      owner_id: ownerId.value,
      period: period.value,
      format
    })

    if (res.status === 'completed') {
      exportMessage.value = `Relevé ${format.toUpperCase()} généré (audit ${res.audit_event_id}).`
    }
  } catch (err) {
    // An export without a server endpoint is reported as unavailable, never as a generated file.
    exportMessage.value = err instanceof Error ? err.message : 'Erreur lors de l’export.'
  } finally {
    isExporting.value = false
  }
}

const kpis = computed<KpiItem[]>(() => statement.value ? [
  { key: 'net', label: 'Revenu net admissible', value: formatMoney(statement.value.totals.eligible_net_revenue) },
  { key: 'due', label: 'Montant dû au propriétaire', value: formatMoney(statement.value.totals.owner_amount_due), positive: true }
] : [])

function formatMoney(amount: number): string {
  return formatCurrency(amount)
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('fr-CA', {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

onMounted(() => {
  loadStatement()
})
</script>
