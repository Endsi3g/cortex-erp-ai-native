<template>
  <div class="space-y-6 max-w-6xl mx-auto" data-test="screen-transaction-composer">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-cortex-border">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-xl font-bold text-cortex-text-primary tracking-tight">
            {{ t('routes.rental_composer') }}
          </h1>
          <span class="px-2 py-0.5 rounded-full bg-cortex-primary-100 text-cortex-primary-800 text-[11px] font-semibold">
            Assistant 3 Étapes
          </span>
        </div>
        <p class="text-xs text-cortex-text-secondary mt-1">
          Création pas-à-pas d'un devis ou réservation avec application de la règle tarifaire 7j = 3j.
        </p>
      </div>

      <RouterLink
        to="/app/cortex-rentals"
        class="cx-btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
      >
        <ArrowLeft class="w-3.5 h-3.5" />
        <span>Retour aux Locations</span>
      </RouterLink>
    </div>

    <!-- Stepper Navigation -->
    <ComposerStepper
      :current-step="currentStep"
      @change-step="currentStep = $event"
    />

    <!-- Wizard Main Area with Lateral Summary -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      <!-- Active Step Component (2 Cols) -->
      <div class="lg:col-span-2">
        <!-- Step 1: Client & Dates -->
        <StepClientDates
          v-if="currentStep === 1"
          v-model="step1Data"
          @next="currentStep = 2"
        />

        <!-- Step 2: Equipment & Pricing -->
        <StepEquipmentPricing
          v-else-if="currentStep === 2"
          v-model:lines="equipmentLines"
          :starts-at="step1Data.startsAt"
          :ends-at="step1Data.endsAt"
          @prev="currentStep = 1"
          @next="currentStep = 3"
        />

        <!-- Step 3: Review & Create -->
        <StepReviewCreate
          v-else-if="currentStep === 3"
          :step1="step1Data"
          :lines="equipmentLines"
          @prev="currentStep = 2"
        />
      </div>

      <!-- Lateral Summary Drawer (1 Col) -->
      <div class="lg:col-span-1">
        <div class="sticky top-4 rounded-xl border border-cortex-border bg-cortex-surface p-4 text-xs space-y-2">
          <h2 class="font-bold uppercase tracking-wider">Résumé</h2>
          <p>Client : <strong>{{ step1Data.customerName || 'À sélectionner' }}</strong></p>
          <p>Période : {{ step1Data.startsAt || '—' }} → {{ step1Data.endsAt || '—' }}</p>
          <p>Articles : {{ totalEquipmentCount }}</p>
          <p class="border-t pt-2 text-cortex-text-muted">Le montant confirmé est calculé par le serveur lors de la vérification.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import ComposerStepper from '../components/composer/ComposerStepper.vue'
import StepClientDates, { type ComposerStep1Data } from '../components/composer/StepClientDates.vue'
import StepEquipmentPricing, { type ComposerLineItem } from '../components/composer/StepEquipmentPricing.vue'
import StepReviewCreate from '../components/composer/StepReviewCreate.vue'

const { t } = useI18n()
const route = useRoute()

const currentStep = ref<number>(1)

const step1Data = ref<ComposerStep1Data>({
  customerId: '',
  customerName: '',
  customerEmail: '',
  startsAt: '',
  endsAt: '',
  projectName: '',
  notes: ''
})

const equipmentLines = ref<ComposerLineItem[]>([])

// Pre-filling from route query (Flow 2 from Matrix)
onMounted(async () => {
  const qStarts = route.query.starts_at
  const qEnds = route.query.ends_at
  const qItems = route.query.items

  if (typeof qStarts === 'string' && qStarts) {
    step1Data.value.startsAt = qStarts
  }
  if (typeof qEnds === 'string' && qEnds) {
    step1Data.value.endsAt = qEnds
  }
  if (typeof qItems === 'string' && qItems) {
    const itemCodes = qItems.split(',').map(s => s.trim()).filter(Boolean)
    const newLines: ComposerLineItem[] = []
    for (const code of itemCodes) {
      let cat
      try { cat = (await getCortexApiClient().searchRentalCatalog(code)).find(c => c.item_code === code) } catch { cat = undefined }
      if (cat) {
        newLines.push({
          itemCode: cat.item_code,
          itemName: cat.item_name,
          category: cat.category,
          dailyRate: cat.daily_rate,
          quantity: 1,
          assignedSerials: []
        })
      }
    }
    if (newLines.length > 0) {
      equipmentLines.value = newLines
    }
  }

})

const totalEquipmentCount = computed(() => {
  return equipmentLines.value.reduce((sum, line) => sum + line.quantity, 0)
})

</script>
