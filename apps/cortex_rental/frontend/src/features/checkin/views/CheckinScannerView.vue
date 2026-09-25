<template>
  <div class="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
    <!-- Top Navigation / Breadcrumbs -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <router-link
          to="/rentals"
          class="p-2 rounded-xl border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-cortex-text-secondary transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Retour aux locations"
        >
          <ArrowLeft class="w-5 h-5" />
        </router-link>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-bold text-cortex-text-primary">
              {{ $t('checkin.title', 'Check-in — Retour Matériel & Diagnostic') }}
            </h1>
            <span class="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-purple-100 text-purple-800">
              F11
            </span>
          </div>
          <p class="text-xs text-cortex-text-muted mt-0.5">
            {{ $t('checkin.subtitle', 'Contrôle retour item par item, retours partiels et anomalies 1-clic') }}
          </p>
        </div>
      </div>

      <!-- Quick Switch Rental Dropdown -->
      <div class="flex items-center gap-2">
        <label for="rental-picker" class="text-xs font-medium text-cortex-text-muted hidden sm:inline">
          Dossier :
        </label>
        <select
          id="rental-picker"
          v-model="selectedRentalId"
          class="px-3 py-2 text-xs font-mono font-semibold rounded-xl border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:ring-2 focus:ring-cortex-primary/30 min-h-[44px]"
          @change="handleSwitchRental"
        >
          <option v-for="option in eligibleRentals" :key="option.id" :value="option.id">{{ option.id }} · {{ option.customer_name }}</option>
        </select>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="p-12 text-center text-cortex-text-muted bg-cortex-surface rounded-2xl border border-cortex-border">
      <Loader2 class="w-8 h-8 animate-spin mx-auto text-cortex-primary mb-2" />
      <span class="text-xs font-semibold">Chargement du dossier de retour...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="loadError" class="p-6 rounded-2xl border border-red-200 bg-red-50 text-red-900 space-y-3">
      <div class="flex items-center gap-2 font-bold text-sm">
        <AlertTriangle class="w-5 h-5 text-red-600" />
        <span>Erreur de chargement du dossier {{ routeRentalId }}</span>
      </div>
      <p class="text-xs text-red-800">{{ loadError }}</p>
      <button
        type="button"
        class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-semibold min-h-[44px]"
        @click="loadRentalData(routeRentalId)"
      >
        Réessayer
      </button>
    </div>

    <template v-else-if="rental">
      <!-- State Warning if not Checked Out or Partially Returned -->
      <div
        v-if="rental.rental_state !== 'Checked Out'"
        class="p-4 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 space-y-2"
      >
        <div class="flex items-center gap-2 text-sm font-bold">
          <AlertTriangle class="w-5 h-5 text-amber-600" />
          <span>Statut actuel : {{ rental.rental_state }}</span>
        </div>
        <p class="text-xs text-amber-800">
          Ce dossier n'est pas en statut Checked Out. Choisissez une location sortie ou demandez a un gestionnaire de verifier son statut.
        </p>
        <button
          type="button"
          class="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition-colors min-h-[44px]"
          v-if="eligibleRentals.length"
          @click="selectRental(eligibleRentals[0]!.id)"
        >
          Ouvrir une location sortie
        </button>
      </div>

      <!-- Success Return Banner (Flow 3 complete) -->
      <div
        v-if="returnSuccess"
        class="p-5 rounded-2xl border border-emerald-300 bg-emerald-50 text-emerald-950 space-y-3 animate-in fade-in"
      >
        <div class="flex items-center gap-2.5">
          <span class="p-2 rounded-xl bg-emerald-100 text-emerald-700">
            <CheckCircle2 class="w-6 h-6" />
          </span>
          <div>
            <h2 class="text-base font-bold">
              {{ returnCompletedState === 'Returned' ? 'Retour clôturé avec succès !' : 'Retour partiel enregistré !' }}
            </h2>
            <p class="text-xs text-emerald-800 mt-0.5">
              Équipements réintégrés au stock et journal d'audit append-only mis à jour.
            </p>
          </div>
        </div>
        <div class="flex items-center gap-3 pt-2">
          <router-link
            :to="`/rentals/${rental.id}`"
            class="px-4 py-2.5 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold transition-colors min-h-[44px] flex items-center gap-2"
          >
            <span>Consulter la fiche 360°</span>
            <ArrowRight class="w-4 h-4" />
          </router-link>
          <button
            type="button"
            class="px-4 py-2.5 rounded-xl border border-emerald-300 bg-emerald-100/60 hover:bg-emerald-100 text-emerald-900 text-xs font-semibold transition-colors min-h-[44px]"
            @click="returnSuccess = false"
          >
            Poursuivre sur cette page
          </button>
        </div>
      </div>

      <!-- Rental Header Card -->
      <div class="p-5 rounded-2xl border border-cortex-border bg-cortex-surface space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div class="flex items-center gap-2">
              <span class="text-lg font-bold font-mono text-cortex-text-primary">{{ rental.id }}</span>
              <span class="px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-800">
                {{ rental.rental_state }}
              </span>
            </div>
            <div class="text-xs text-cortex-text-secondary mt-1">
              Client : <strong>{{ rental.customer_name }}</strong>
              <span v-if="rental.project_name" class="ml-2 text-cortex-text-muted">| Projet : {{ rental.project_name }}</span>
            </div>
          </div>

          <!-- Counters / Progress -->
          <div class="flex items-center gap-3">
            <div class="text-right">
              <div class="text-xs text-cortex-text-muted font-medium">Progression du retour</div>
              <div class="text-base font-mono font-bold text-cortex-text-primary">
                {{ totalReturnedOrProcessedCount }} / {{ totalExpectedCount }} items
              </div>
            </div>
            <div class="w-24 bg-cortex-surface-muted rounded-full h-3 overflow-hidden border border-cortex-border">
              <div
                class="h-full transition-all duration-300"
                :class="progressPercentage === 100 ? 'bg-emerald-500' : 'bg-cortex-primary'"
                :style="{ width: `${progressPercentage}%` }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 52px Scanner Input (Persistent Autofocus & Cadence) -->
      <div class="p-5 rounded-2xl border-2 border-cortex-primary/30 bg-cortex-surface shadow-sm space-y-3">
        <div class="flex items-center justify-between">
          <label for="checkin-scanner" class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cortex-text-primary">
            <ScanLine class="w-4 h-4 text-cortex-primary" />
            <span>Scanner Haute Cadence — Retour Inventaire</span>
          </label>
          <span class="text-[11px] text-cortex-text-muted font-mono">
            Autofocus actif • 52px tactile
          </span>
        </div>

        <CortexScannerInput
          id="checkin-scanner"
          ref="scannerInputRef"
          v-model="scanBuffer"
          :disabled="isScanning"
          placeholder="Scanner le code-barres / numéro de série de retour..."
          @scan="handleBarcodeScan"
        />

        <!-- Scan Notification Feedback -->
        <div
          v-if="scanFeedback"
          class="p-3 rounded-xl text-xs flex items-center justify-between animate-in fade-in"
          :class="scanFeedback.type === 'success' ? 'bg-emerald-50 text-emerald-900 border border-emerald-200' : 'bg-red-50 text-red-900 border border-red-200'"
        >
          <span class="flex items-center gap-2">
            <CheckCircle2 v-if="scanFeedback.type === 'success'" class="w-4 h-4 text-emerald-600" />
            <AlertTriangle v-else class="w-4 h-4 text-red-600" />
            <span>{{ scanFeedback.message }}</span>
          </span>
          <button
            type="button"
            class="text-[10px] uppercase font-bold tracking-wider hover:underline"
            @click="scanFeedback = null"
          >
            Fermer
          </button>
        </div>
      </div>

      <!-- Equipment Return Checklist & 1-Click Anomaly Bar -->
      <div class="p-5 rounded-2xl border border-cortex-border bg-cortex-surface space-y-4">
        <div class="flex items-center justify-between border-b border-cortex-border pb-3">
          <h2 class="text-sm font-bold text-cortex-text-primary uppercase tracking-wider">
            Équipements à réceptionner ({{ rental.items.length }} lignes)
          </h2>
          <span class="text-xs text-cortex-text-muted">
            1-Clic pour déclarer les anomalies
          </span>
        </div>

        <div class="space-y-4">
          <div
            v-for="item in rental.items"
            :key="item.id"
            class="p-4 rounded-xl border border-cortex-border bg-cortex-surface-muted/50 space-y-3"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div class="text-sm font-bold text-cortex-text-primary">{{ item.item_name }}</div>
                <div class="text-xs font-mono text-cortex-text-muted mt-0.5">
                  Code : {{ item.item_code }} | Quantité totale : {{ item.quantity }}
                </div>
              </div>
              <div class="text-xs font-mono font-bold">
                <span class="px-2.5 py-1 rounded-lg bg-cortex-surface border border-cortex-border">
                  {{ getItemScannedCount(item) }} / {{ item.quantity }} retournés
                </span>
              </div>
            </div>

            <!-- Serials List with Status & 1-Click Triggers -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2">
              <div
                v-for="sn in item.assigned_serials"
                :key="sn"
                class="p-3 rounded-xl border bg-cortex-surface flex flex-wrap items-center justify-between gap-2 transition-all"
                :class="getSerialCardClass(sn)"
              >
                <div>
                  <div class="font-mono text-xs font-bold text-cortex-text-primary flex items-center gap-1.5">
                    <span>{{ sn }}</span>
                    <span
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      :class="getSerialBadgeClass(sn)"
                    >
                      {{ getSerialStatusText(sn) }}
                    </span>
                  </div>
                  <div v-if="damagedSerials[sn]" class="text-[11px] text-red-700 mt-0.5 font-medium">
                    Dommage : {{ damagedSerials[sn].severity }} ({{ damagedSerials[sn].description }})
                  </div>
                  <div v-if="missingSerials.includes(sn)" class="text-[11px] text-amber-700 mt-0.5 font-medium">
                    Signalé manquant
                  </div>
                </div>

                <!-- 1-Click Anomaly Action Buttons -->
                <div class="flex items-center gap-1.5 shrink-0">
                  <!-- Quick checkin button if pending -->
                  <button
                    v-if="!isSerialProcessed(sn)"
                    type="button"
                    class="px-2.5 py-1.5 rounded-lg border border-emerald-300 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold transition-colors min-h-[36px]"
                    title="Valider le retour direct"
                    @click="handleManualCheckin(sn)"
                  >
                    ✓ Retourner
                  </button>

                  <!-- 1-Click Missing -->
                  <button
                    type="button"
                    class="px-2 py-1.5 rounded-lg border text-xs font-semibold transition-colors min-h-[36px]"
                    :class="missingSerials.includes(sn) ? 'border-amber-400 bg-amber-200 text-amber-900' : 'border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-800'"
                    :title="missingSerials.includes(sn) ? 'Annuler manquant' : 'Marquer comme manquant'"
                    @click="handleToggleMissing(sn)"
                  >
                    📦 Manquant
                  </button>

                  <!-- 1-Click Damage -->
                  <button
                    type="button"
                    class="px-2 py-1.5 rounded-lg border text-xs font-semibold transition-colors min-h-[36px]"
                    :class="damagedSerials[sn] ? 'border-red-400 bg-red-200 text-red-900' : 'border-red-200 bg-red-50 hover:bg-red-100 text-red-800'"
                    title="Déclarer un bris ou dommage"
                    @click="openDamageModal(sn, item.item_name)"
                  >
                    📷 Casse
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Footer: Partial Return / Close Return -->
      <div class="p-5 rounded-2xl border border-cortex-border bg-cortex-surface flex flex-wrap items-center justify-between gap-4">
        <div>
          <span class="text-xs font-bold text-cortex-text-secondary block">
            Actions d'achèvement de session
          </span>
          <span class="text-[11px] text-cortex-text-muted">
            Enregistrer le reliquat partiel ou valider le contrôle de fin de location
          </span>
        </div>

        <div class="flex items-center gap-3">
          <button
            type="button"
            class="px-4 py-2.5 rounded-xl border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-xs font-semibold text-cortex-text-secondary transition-colors min-h-[44px]"
            :disabled="isSubmittingAction"
            @click="handlePartialReturn"
          >
            <Loader2 v-if="isSubmittingAction" class="w-4 h-4 animate-spin inline mr-1" />
            <span>{{ $t('checkin.partial_return_btn', 'Enregistrer Retour Partiel') }}</span>
          </button>

          <button
            type="button"
            class="px-5 py-2.5 rounded-xl bg-cortex-primary hover:bg-cortex-primary-hover text-white text-xs font-bold shadow-sm transition-colors min-h-[44px] flex items-center gap-2"
            :disabled="isSubmittingAction"
            @click="showDiffModal = true"
          >
            <span>{{ $t('checkin.close_return_btn', 'Clôturer le Retour...') }}</span>
            <ArrowRight class="w-4 h-4" />
          </button>
        </div>
      </div>
    </template>

    <!-- Modals -->
    <DamageEvidenceModal
      :is-open="showDamageModal"
      :rental-id="rental?.id || ''"
      :serial-number="activeDamageSerial"
      :item-name="activeDamageItemName"
      @close="showDamageModal = false"
      @submitted="handleDamageSubmitted"
    />

    <ReturnDiffSummary
      v-if="rental"
      :rental="rental"
      :missing-serials="missingSerials"
      :damaged-serials="Object.keys(damagedSerials)"
      :returned-serials="returnedSerials"
      :is-open="showDiffModal"
      :is-submitting="isSubmittingAction"
      @close="showDiffModal = false"
      @confirm="handleConfirmCloseReturn"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Loader2,
  ScanLine
} from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { RentalTransaction, RentalLineItem } from '@/api/contracts'
import { ScannerFeedback, sanitizeBarcodeInput } from '@/utils/scanner'
import CortexScannerInput from '@/design-system/components/base/CortexScannerInput.vue'
import DamageEvidenceModal from '../components/DamageEvidenceModal.vue'
import ReturnDiffSummary from '../components/ReturnDiffSummary.vue'

const route = useRoute()
const router = useRouter()

const routeRentalId = computed(() => (route.params.rental as string) || '')
const selectedRentalId = ref(routeRentalId.value)
const eligibleRentals = ref<Array<{ id: string; customer_name: string }>>([])

const rental = ref<RentalTransaction | null>(null)
const isLoading = ref(true)
const loadError = ref('')

const scanBuffer = ref('')
const isScanning = ref(false)
const scannerInputRef = ref<InstanceType<typeof CortexScannerInput> | null>(null)

// Tracking local return states
const returnedSerials = ref<string[]>([])
const missingSerials = ref<string[]>([])
const damagedSerials = ref<Record<string, { severity: string; description: string; fileName?: string }>>({})

// Modals
const showDamageModal = ref(false)
const activeDamageSerial = ref('')
const activeDamageItemName = ref('')
const showDiffModal = ref(false)
const isSubmittingAction = ref(false)
const returnSuccess = ref(false)
const returnCompletedState = ref<'Returned' | 'Partially Returned'>('Returned')

// Feedback toast
const scanFeedback = ref<{ type: 'success' | 'error'; message: string } | null>(null)

const totalExpectedCount = computed(() => {
  if (!rental.value) return 0
  return rental.value.items.reduce((sum, item) => sum + item.quantity, 0)
})

const totalReturnedOrProcessedCount = computed(() => {
  return returnedSerials.value.length + missingSerials.value.length
})

const progressPercentage = computed(() => {
  if (totalExpectedCount.value === 0) return 0
  return Math.min(100, Math.round((totalReturnedOrProcessedCount.value / totalExpectedCount.value) * 100))
})

async function loadRentalData(id: string) {
  isLoading.value = true
  loadError.value = ''
  try {
    const client = getCortexApiClient()
    const data = await client.getRental({ id })
    rental.value = data
    selectedRentalId.value = id

    // Populate already scanned items if present
    const alreadyReturned: string[] = []
    for (const item of data.items) {
      if (item.scanned_checkin_serials) {
        alreadyReturned.push(...item.scanned_checkin_serials)
      }
    }
    returnedSerials.value = Array.from(new Set(alreadyReturned))
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : 'Impossible de récupérer la transaction.'
  } finally {
    isLoading.value = false
  }
}

function handleSwitchRental() {
  selectRental(selectedRentalId.value)
}

function selectRental(id: string) {
  router.push(`/checkin/${id}`)
  loadRentalData(id)
}

function isSerialProcessed(sn: string): boolean {
  return returnedSerials.value.includes(sn) || missingSerials.value.includes(sn)
}

function getItemScannedCount(item: RentalLineItem): number {
  return (item.assigned_serials || []).filter((sn: string) => returnedSerials.value.includes(sn)).length
}

function getSerialStatusText(sn: string): string {
  if (damagedSerials.value[sn]) return 'Endommagé'
  if (missingSerials.value.includes(sn)) return 'Manquant'
  if (returnedSerials.value.includes(sn)) return 'Retourné'
  return 'En attente'
}

function getSerialBadgeClass(sn: string): string {
  if (damagedSerials.value[sn]) return 'bg-red-100 text-red-800'
  if (missingSerials.value.includes(sn)) return 'bg-amber-100 text-amber-800'
  if (returnedSerials.value.includes(sn)) return 'bg-emerald-100 text-emerald-800'
  return 'bg-slate-100 text-slate-700'
}

function getSerialCardClass(sn: string): string {
  if (damagedSerials.value[sn]) return 'border-red-300 bg-red-50/40'
  if (missingSerials.value.includes(sn)) return 'border-amber-300 bg-amber-50/40'
  if (returnedSerials.value.includes(sn)) return 'border-emerald-300 bg-emerald-50/40'
  return 'border-cortex-border'
}

async function handleBarcodeScan(input: { raw: string; trimmed: string } | string) {
  const rawBarcode = typeof input === 'string' ? input : input.trimmed
  const barcode = sanitizeBarcodeInput(rawBarcode)
  if (!barcode || !rental.value) return

  // Check duplicate
  if (returnedSerials.value.includes(barcode)) {
    ScannerFeedback.playError()
    scanFeedback.value = {
      type: 'error',
      message: `Attention : Le numéro de série ${barcode} a déjà été scanné pour ce retour.`
    }
    return
  }

  // Find if this serial belongs to this rental
  const matchingItem = rental.value.items.find(it => it.assigned_serials.includes(barcode))
  if (!matchingItem) {
    ScannerFeedback.playError()
    scanFeedback.value = {
      type: 'error',
      message: `Équipement ${barcode} non associé à ce contrat (${rental.value.id}).`
    }
    return
  }

  // Valid scan
  isScanning.value = true
  try {
    const client = getCortexApiClient()
    const res = await client.scanCheckinSerial({
      rental_id: rental.value.id,
      serial_number: barcode,
      condition: 'Good'
    })

    if (res.status === 'completed') {
      ScannerFeedback.playSuccess()
      if (!returnedSerials.value.includes(barcode)) {
        returnedSerials.value.push(barcode)
      }
      // If was previously marked missing, unmark
      missingSerials.value = missingSerials.value.filter(s => s !== barcode)

      scanFeedback.value = {
        type: 'success',
        message: `✓ Numéro de série ${barcode} (${matchingItem.item_name}) enregistré avec succès.`
      }
    } else {
      ScannerFeedback.playError()
      scanFeedback.value = {
        type: 'error',
        message: res.errors?.[0]?.message || 'Erreur lors du scan de retour.'
      }
    }
  } catch (err) {
    ScannerFeedback.playError()
    scanFeedback.value = {
      type: 'error',
      message: err instanceof Error ? err.message : 'Erreur de communication API.'
    }
  } finally {
    isScanning.value = false
    scanBuffer.value = ''
  }
}

async function handleManualCheckin(sn: string) {
  await handleBarcodeScan(sn)
}

async function handleToggleMissing(sn: string) {
  if (!rental.value) return

  if (missingSerials.value.includes(sn)) {
    missingSerials.value = missingSerials.value.filter(s => s !== sn)
  } else {
    // Call markSerialMissing
    try {
      const client = getCortexApiClient()
      await client.markSerialMissing({
        rental_id: rental.value.id,
        serial_number: sn,
        reason: 'Déclaré manquant au retour'
      })
      missingSerials.value.push(sn)
      returnedSerials.value = returnedSerials.value.filter(s => s !== sn)
      ScannerFeedback.playSuccess()
    } catch {
      ScannerFeedback.playError()
    }
  }
}

function openDamageModal(sn: string, itemName: string) {
  activeDamageSerial.value = sn
  activeDamageItemName.value = itemName
  showDamageModal.value = true
}

function handleDamageSubmitted(data: { serialNumber: string; severity: string; description: string; photoUploadId?: string }) {
  damagedSerials.value[data.serialNumber] = {
    severity: data.severity,
    description: data.description,
    ...(data.photoUploadId ? { fileName: data.photoUploadId } : {})
  }
  if (!returnedSerials.value.includes(data.serialNumber)) {
    returnedSerials.value.push(data.serialNumber)
  }
  missingSerials.value = missingSerials.value.filter(s => s !== data.serialNumber)
  ScannerFeedback.playSuccess()
}

function makeCheckinItems(includeMissing: boolean) {
  if (!rental.value) return []
  const returned = new Set(returnedSerials.value)
  const missing = new Set(missingSerials.value)
  return rental.value.items.flatMap(line => line.assigned_serials.flatMap(serial => {
    const damage = damagedSerials.value[serial]
    const isMissing = missing.has(serial)
    if (!returned.has(serial) && !(includeMissing && isMissing)) return []
    const severity = damage?.severity
    const disposition: 'Missing' | 'Quarantine' | 'Repair' | 'Return to Stock' = isMissing ? 'Missing' : severity === 'unusable' ? 'Quarantine' : severity === 'major' ? 'Repair' : damage ? 'Quarantine' : 'Return to Stock'
    const damageSeverity: 'Blocking' | 'Functional' | 'Cosmetic' | 'None' = severity === 'unusable' ? 'Blocking' : severity === 'major' ? 'Functional' : damage ? 'Cosmetic' : 'None'
    return [{ transaction_item: line.id, item_code: line.item_code, serial_no: serial,
      expected_qty: 1, returned_qty: isMissing ? 0 : 1,
      condition: damage ? 'Damaged' as const : 'Good' as const, disposition, damage_severity: damageSeverity,
      notes: damage?.description || (isMissing ? 'Declare manquant au retour' : ''),
      ...(damage?.fileName ? { file_name: damage.fileName } : {}) }]
  }))
}

async function handlePartialReturn() {
  if (!rental.value) return
  isSubmittingAction.value = true
  try {
    const res = await getCortexApiClient().completePartialReturn({ rental_id: rental.value.id,
      notes: 'Retour partiel valide au scanner', finalize_mode: 'partial', items: makeCheckinItems(false) })
    if (res.status !== 'completed' || !res.mutation_performed) throw new Error(res.errors?.[0]?.message || "Le serveur n'a pas confirme ce retour.")
    returnCompletedState.value = 'Partially Returned'; returnSuccess.value = true
    await loadRentalData(rental.value.id)
  } catch (err) { scanFeedback.value = { type: 'error', message: err instanceof Error ? err.message : 'Erreur lors du retour partiel.' } }
  finally { isSubmittingAction.value = false }
}

async function handleConfirmCloseReturn() {
  if (!rental.value) return
  isSubmittingAction.value = true
  try {
    const mode = missingSerials.value.length ? 'settle_with_loss' : 'full'
    const res = await getCortexApiClient().completePartialReturn({ rental_id: rental.value.id,
      notes: `Cloture: ${returnedSerials.value.length} recus, ${missingSerials.value.length} manquants, ${Object.keys(damagedSerials.value).length} dommages`,
      finalize_mode: mode, items: makeCheckinItems(true) })
    if (res.status !== 'completed' || !res.mutation_performed) throw new Error(res.errors?.[0]?.message || "Le serveur n'a pas confirme la cloture.")
    showDiffModal.value = false; returnCompletedState.value = 'Returned'; returnSuccess.value = true
    await loadRentalData(rental.value.id)
  } catch (err) { scanFeedback.value = { type: 'error', message: err instanceof Error ? err.message : 'Erreur lors de la cl?ture.' } }
  finally { isSubmittingAction.value = false }
}

onMounted(() => {
  void getCortexApiClient().listRentals({ page: 1, page_size: 100, state: 'Checked Out' }).then(result => { eligibleRentals.value = result.items.map(item => ({ id: item.id, customer_name: item.customer_name })) }).catch(() => { eligibleRentals.value = [] })
  if (routeRentalId.value) loadRentalData(routeRentalId.value)
})
</script>
