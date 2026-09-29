<template>
  <div class="cx-page" data-test="screen-transaction-composer">
    <CortexPageHeader
      :title="t('routes.rental_composer')"
      subtitle="Devis ou réservation en trois étapes ; le montant est calculé par le serveur (règle 7 j = 3 j)."
      :provenance="isMock ? 'mock' : 'api'"
    >
      <template #actions><RouterLink to="/app/cortex-rentals" class="cx-btn-secondary">Toutes les locations</RouterLink></template>
    </CortexPageHeader>

    <div class="cx-section">
      <ComposerStepper
        :current-step="currentStep"
        @change-step="currentStep = $event"
      />
    </div>

    <div class="cx-section grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
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
        <aside class="cx-card" aria-labelledby="composer-summary">
          <h2 id="composer-summary" class="m-0 mb-2 text-sm font-semibold">Résumé</h2>
          <dl class="cx-dl" style="grid-template-columns: 1fr">
            <div><dt>Client</dt><dd>{{ step1Data.customerName || 'À sélectionner' }}</dd></div>
            <div><dt>Période</dt><dd>{{ step1Data.startsAt || '—' }} → {{ step1Data.endsAt || '—' }}</dd></div>
            <div><dt>Articles</dt><dd>{{ totalEquipmentCount }}</dd></div>
          </dl>
          <p class="cx-caption" style="padding: 8px 0 0">Le montant confirmé est calculé par le serveur lors de la vérification.</p>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getCortexApiClient } from '@/api'
import { MockCortexApiClient } from '@/api/mock/MockCortexApiClient'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import ComposerStepper from '../components/composer/ComposerStepper.vue'
import StepClientDates, { type ComposerStep1Data } from '../components/composer/StepClientDates.vue'
import StepEquipmentPricing, { type ComposerLineItem } from '../components/composer/StepEquipmentPricing.vue'
import StepReviewCreate from '../components/composer/StepReviewCreate.vue'

const { t } = useI18n()
const route = useRoute()

const currentStep = ref<number>(1)
const isMock = getCortexApiClient() instanceof MockCortexApiClient

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
