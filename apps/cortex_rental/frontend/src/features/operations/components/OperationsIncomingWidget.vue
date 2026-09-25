<template>
  <div class="rounded-xl border border-cortex-border bg-cortex-surface p-5 shadow-2xs" data-test="operations-incoming-widget">
    <div class="flex items-center justify-between pb-3 border-b border-cortex-border">
      <div class="flex items-center gap-2">
        <Sparkles class="w-5 h-5 text-cortex-primary-600" />
        <h2 class="text-sm font-bold text-cortex-text-primary">{{ t('operations.incoming_title') }}</h2>
      </div>
      <span class="px-2 py-0.5 rounded bg-cortex-primary-100 text-cortex-primary-800 text-[11px] font-bold font-mono">
        Onyx Intake
      </span>
    </div>

    <div class="mt-3 space-y-3">
      <div
        v-for="req in items"
        :key="req.id"
        class="p-3 rounded-lg border border-cortex-border bg-cortex-surface-secondary/40 hover:border-cortex-primary-300 transition-colors"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <Mail class="w-3.5 h-3.5 text-cortex-text-muted" />
            <span class="text-xs font-semibold text-cortex-text-primary">{{ req.sourceTitle }}</span>
          </div>
          <AiStatusBadge state="extracted" size="sm" />
        </div>

        <div class="mt-2 text-[11px] text-cortex-text-secondary">
          <p><strong>Client :</strong> {{ req.customer }}</p>
          <p><strong>Équipement demandé :</strong> {{ req.requestedEquipment }}</p>
          <p><strong>Dates estimées :</strong> {{ req.dates }}</p>
        </div>

        <div class="mt-2.5 pt-2 border-t border-cortex-border flex items-center justify-between">
          <div class="flex items-center gap-1">
            <span class="text-[10px] text-cortex-text-muted">Confiance :</span>
            <span class="text-[11px] font-bold text-cortex-primary-700 font-mono">{{ req.confidence }}%</span>
          </div>
          <RouterLink
            :to="req.composerUrl"
            class="cx-btn-secondary text-[11px] px-2.5 py-1"
          >
            Créer devis →
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Sparkles, Mail } from 'lucide-vue-next'
import AiStatusBadge from '@/design-system/components/ai/AiStatusBadge.vue'

const { t } = useI18n()

interface IncomingItem {
  id: string
  sourceTitle: string
  customer: string
  requestedEquipment: string
  dates: string
  confidence: number
  composerUrl: string
}

const items: IncomingItem[] = [
  {
    id: 'inb-01',
    sourceTitle: 'Demande Devis Tournage Pub',
    customer: 'Production Nord Inc.',
    requestedEquipment: 'ARRI Alexa 35 + 1 Kit Cooke S4/i',
    dates: '12 sept. — 19 sept. 2026',
    confidence: 94,
    composerUrl: '/rentals/new?items=DEMO-ITM-ALX35,DEMO-ITM-CKE-S4&starts_at=2026-09-12&ends_at=2026-09-19'
  },
  {
    id: 'inb-02',
    sourceTitle: 'PDF Bon de Commande Extrait',
    customer: 'Studio Lumière Montréal',
    requestedEquipment: 'RED V-Raptor XL 8K Production Pack',
    dates: '20 sept. — 23 sept. 2026',
    confidence: 88,
    composerUrl: '/rentals/new?items=DEMO-ITM-VRP8K&starts_at=2026-09-20&ends_at=2026-09-23'
  }
]
</script>
