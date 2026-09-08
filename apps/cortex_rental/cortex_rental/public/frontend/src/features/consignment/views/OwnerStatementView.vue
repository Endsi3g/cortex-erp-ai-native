<template>
  <div class="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
    <!-- Top Nav / Back Link -->
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <router-link
          to="/app/cortex-consignment"
          class="p-2 rounded-xl border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-cortex-text-secondary transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Retour au tableau de bord consignation"
        >
          <ArrowLeft class="w-5 h-5" />
        </router-link>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-bold text-cortex-text-primary">
              {{ $t('consignment.statement_title', 'Relevé Propriétaire Étanche') }}
            </h1>
            <span class="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
              F14 • OwnerStatementSafe
            </span>
          </div>
          <p class="text-xs text-cortex-text-muted mt-0.5">
            {{ $t('consignment.statement_subtitle', 'Décompte financier certifié sans fuite de données locataires') }}
          </p>
        </div>
      </div>

      <!-- Export Buttons -->
      <div v-if="statement" class="flex items-center gap-2">
        <button
          type="button"
          class="px-3.5 py-2 rounded-xl border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-xs font-semibold text-cortex-text-primary transition-colors min-h-[44px] flex items-center gap-1.5 disabled:opacity-50"
          :disabled="isExporting"
          @click="handleExport('csv')"
        >
          <FileSpreadsheet class="w-4 h-4 text-emerald-600" />
          <span>Exporter CSV</span>
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-xl bg-cortex-primary hover:bg-cortex-primary-hover text-white text-xs font-bold transition-colors min-h-[44px] flex items-center gap-1.5 shadow-xs disabled:opacity-50"
          :disabled="isExporting"
          @click="handleExport('pdf')"
        >
          <FileText class="w-4 h-4" />
          <span>Exporter PDF Certifié</span>
        </button>
      </div>
    </div>

    <!-- Mandatory Permanent Privacy Banner -->
    <div
      class="p-4 rounded-2xl border-2 border-emerald-500 bg-emerald-50/90 text-xs text-emerald-950 font-medium flex items-center justify-between gap-3 shadow-xs"
      data-test="privacy-banner"
    >
      <div class="flex items-center gap-2.5">
        <span class="p-2 rounded-xl bg-emerald-100 text-emerald-700 shrink-0">
          <ShieldCheck class="w-5 h-5" />
        </span>
        <div>
          <span class="font-bold text-emerald-900 block text-xs uppercase tracking-wider">
            Bannière Permanente de Confidentialité
          </span>
          <span class="text-xs text-emerald-800">
            Informations clients exclues pour la confidentialité des locations.
          </span>
        </div>
      </div>
      <span class="text-[11px] font-mono font-bold bg-emerald-200/80 px-2 py-1 rounded text-emerald-900 shrink-0 hidden sm:inline-block">
        PRD-CON • Strict Safe
      </span>
    </div>

    <!-- Export Feedback Alert -->
    <div
      v-if="exportMessage"
      class="p-3.5 bg-emerald-50 border border-emerald-300 rounded-xl text-xs text-emerald-900 flex items-center justify-between animate-in fade-in"
    >
      <span class="flex items-center gap-2">
        <CheckCircle2 class="w-4 h-4 text-emerald-600" />
        <span>{{ exportMessage }}</span>
      </span>
      <button
        type="button"
        class="text-[10px] font-bold uppercase hover:underline"
        @click="exportMessage = ''"
      >
        Fermer
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="p-12 text-center text-cortex-text-muted bg-cortex-surface rounded-2xl border border-cortex-border">
      <Loader2 class="w-8 h-8 animate-spin mx-auto text-cortex-primary mb-2" />
      <span class="text-xs font-semibold">Génération du relevé étanche...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage" class="p-6 rounded-2xl border border-red-200 bg-red-50 text-red-900 space-y-3">
      <div class="flex items-center gap-2 font-bold text-sm">
        <AlertTriangle class="w-5 h-5 text-red-600" />
        <span>Erreur de chargement du relevé</span>
      </div>
      <p class="text-xs text-red-800">{{ errorMessage }}</p>
      <button
        type="button"
        class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-semibold min-h-[44px]"
        @click="loadStatement"
      >
        Réessayer
      </button>
    </div>

    <template v-else-if="statement">
      <!-- Statement Card -->
      <div class="bg-cortex-surface border border-cortex-border rounded-2xl p-6 space-y-6 shadow-sm">
        <!-- Certified Header Info -->
        <div class="flex flex-wrap items-start justify-between gap-6 border-b border-cortex-border pb-6">
          <div class="space-y-1">
            <span class="text-[11px] font-mono uppercase tracking-wider text-cortex-text-muted">
              Relevé Mensuel de Consignation
            </span>
            <h2 class="text-xl font-bold text-cortex-text-primary">
              {{ statement.owner.display_name }}
            </h2>
            <div class="text-xs text-cortex-text-muted flex items-center gap-2">
              <span>Code Partenaire : <strong class="font-mono text-cortex-text-primary">{{ statement.owner.code }}</strong></span>
              <span>•</span>
              <span>ID : <strong class="font-mono">{{ statement.owner.id }}</strong></span>
            </div>
          </div>

          <div class="text-left sm:text-right space-y-1 text-xs text-cortex-text-muted font-mono">
            <div>Période : <strong class="text-cortex-text-primary">{{ statement.period.start }} au {{ statement.period.end }}</strong></div>
            <div>Généré le : {{ formatDate(statement.generated_at) }}</div>
            <div>Snapshot : {{ statement.snapshot_version }}</div>
          </div>
        </div>

        <!-- Totals Summary Banner -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="p-4 rounded-xl bg-cortex-surface-muted border border-cortex-border space-y-1">
            <div class="text-xs font-bold uppercase tracking-wider text-cortex-text-muted">
              Revenu Net Admissible de Location
            </div>
            <div class="text-2xl font-bold font-mono text-cortex-text-primary">
              {{ formatMoney(statement.totals.eligible_net_revenue) }}
            </div>
            <div class="text-[11px] text-cortex-text-muted">
              Facturé aux clients (hors remises et assurances)
            </div>
          </div>

          <div class="p-4 rounded-xl bg-emerald-50 border border-emerald-300 space-y-1">
            <div class="text-xs font-bold uppercase tracking-wider text-emerald-900">
              Montant Total Dû au Propriétaire
            </div>
            <div class="text-2xl font-bold font-mono text-emerald-700">
              {{ formatMoney(statement.totals.owner_amount_due) }}
            </div>
            <div class="text-[11px] text-emerald-800 font-semibold">
              Part contractuelle nette à décaisser
            </div>
          </div>
        </div>

        <!-- Statement Itemized Lines Table -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-xs font-bold uppercase tracking-wider text-cortex-text-primary">
              Ventilation Ligne par Ligne ({{ statement.lines.length }} sorties)
            </h3>
            <span class="text-[11px] text-emerald-700 font-medium flex items-center gap-1">
              <Lock class="w-3.5 h-3.5" />
              <span>Zéro donnée locataire</span>
            </span>
          </div>

          <div class="overflow-x-auto rounded-xl border border-cortex-border">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="bg-cortex-surface-muted border-b border-cortex-border text-cortex-text-muted font-bold uppercase tracking-wider">
                  <th class="py-2.5 px-3">Équipement</th>
                  <th class="py-2.5 px-3">N° de Série</th>
                  <th class="py-2.5 px-3">Période Location</th>
                  <th class="py-2.5 px-3 text-center">Jours Facturés</th>
                  <th class="py-2.5 px-3 text-right">Taux Journalier</th>
                  <th class="py-2.5 px-3 text-center">% Part</th>
                  <th class="py-2.5 px-3 text-right">Montant Propriétaire</th>
                  <th class="py-2.5 px-3 text-right">Réf. Facture</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-cortex-border bg-cortex-surface">
                <tr
                  v-for="line in statement.lines"
                  :key="`${line.serial_number}_${line.rental_start_date}`"
                  class="hover:bg-cortex-surface-muted/40 transition-colors"
                >
                  <td class="py-3 px-3 font-semibold text-cortex-text-primary">
                    {{ line.equipment_name }}
                  </td>
                  <td class="py-3 px-3 font-mono font-bold text-cortex-text-primary">
                    {{ line.serial_number }}
                  </td>
                  <td class="py-3 px-3 font-mono text-cortex-text-muted">
                    {{ line.rental_start_date }} → {{ line.rental_end_date }}
                  </td>
                  <td class="py-3 px-3 font-mono text-center text-cortex-text-primary font-medium">
                    {{ line.billable_days }} j
                  </td>
                  <td class="py-3 px-3 font-mono text-right text-cortex-text-secondary">
                    {{ formatMoney(line.rate) }}
                  </td>
                  <td class="py-3 px-3 font-mono text-center font-bold text-emerald-700">
                    {{ line.consignment_percentage }}%
                  </td>
                  <td class="py-3 px-3 font-mono font-bold text-right text-emerald-700 text-sm">
                    {{ formatMoney(line.owner_amount) }}
                  </td>
                  <td class="py-3 px-3 font-mono text-right text-cortex-text-muted">
                    {{ line.invoice_reference }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Certification & Immutability Notice -->
        <div class="p-4 bg-cortex-surface-muted border border-cortex-border rounded-xl text-xs text-cortex-text-muted flex items-start gap-3">
          <ShieldCheck class="w-5 h-5 text-cortex-primary shrink-0 mt-0.5" />
          <div class="space-y-0.5">
            <div class="font-bold text-cortex-text-primary">Certificat de conformité comptable Cortex</div>
            <p>
              Ce relevé a été scellé selon la version {{ statement.snapshot_version }} des snapshots de facturation. Conformément aux politiques de confidentialité audiovisuelle, aucun identifiant, contact ou nom de client locataire n'est stocké ou transmis dans les exports propriétaires.
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FileSpreadsheet,
  FileText,
  Loader2,
  Lock,
  ShieldCheck
} from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { OwnerStatementSafe } from '@/api/contracts'
import { formatCurrency } from '@/utils/formatters'

const route = useRoute()

const ownerId = computed(() => (route.params.owner as string) || 'DEMO-OWN-001')
const period = computed(() => (route.params.period as string) || '2026-08')

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
      exportMessage.value = `✓ Relevé ${format.toUpperCase()} généré avec succès (Audit: ${res.audit_event_id}).`
    }
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur lors de l’export.'
  } finally {
    isExporting.value = false
  }
}

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
