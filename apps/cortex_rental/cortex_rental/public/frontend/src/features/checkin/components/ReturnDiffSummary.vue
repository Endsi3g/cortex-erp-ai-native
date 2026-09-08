<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto"
    role="dialog"
    aria-modal="true"
    aria-labelledby="return-diff-title"
  >
    <div
      class="bg-cortex-surface border border-cortex-border rounded-2xl shadow-2xl max-w-2xl w-full p-6 space-y-6 animate-in fade-in zoom-in-95 duration-150"
    >
      <!-- Header -->
      <div class="flex items-start justify-between border-b border-cortex-border pb-4">
        <div>
          <div class="flex items-center gap-2">
            <span class="p-1.5 rounded-lg bg-cortex-primary/10 text-cortex-primary">
              <FileCheck class="w-5 h-5" />
            </span>
            <h3 id="return-diff-title" class="text-base font-bold text-cortex-text-primary">
              {{ $t('checkin.diff_title', 'Diff Récapitulatif Avant Clôture') }}
            </h3>
          </div>
          <p class="text-xs text-cortex-text-muted mt-1">
            Contrat <span class="font-mono font-semibold text-cortex-text-primary">{{ rental.id }}</span> — {{ rental.customer_name }}
          </p>
        </div>
        <button
          class="p-2 text-cortex-text-muted hover:text-cortex-text-primary rounded-lg hover:bg-cortex-surface-muted transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Fermer"
          @click="$emit('close')"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- KPI Summary Cards -->
      <div class="grid grid-cols-4 gap-3 text-center">
        <div class="p-3 rounded-xl bg-cortex-surface-muted border border-cortex-border">
          <div class="text-[11px] font-bold text-cortex-text-muted uppercase">Attendus</div>
          <div class="text-xl font-bold font-mono text-cortex-text-primary mt-1">{{ totalExpected }}</div>
        </div>

        <div class="p-3 rounded-xl bg-emerald-50 border border-emerald-200">
          <div class="text-[11px] font-bold text-emerald-800 uppercase">Conformes</div>
          <div class="text-xl font-bold font-mono text-emerald-700 mt-1">{{ returnedSerials.length }}</div>
        </div>

        <div class="p-3 rounded-xl bg-amber-50 border border-amber-200">
          <div class="text-[11px] font-bold text-amber-800 uppercase">Manquants</div>
          <div class="text-xl font-bold font-mono text-amber-700 mt-1">{{ missingSerials.length }}</div>
        </div>

        <div class="p-3 rounded-xl bg-red-50 border border-red-200">
          <div class="text-[11px] font-bold text-red-800 uppercase">Dommages</div>
          <div class="text-xl font-bold font-mono text-red-700 mt-1">{{ damagedSerials.length }}</div>
        </div>
      </div>

      <!-- Reliquat Alert if any items remaining unaccounted -->
      <div
        v-if="unaccountedCount > 0"
        class="p-3.5 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 flex items-start gap-2.5"
      >
        <AlertTriangle class="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
        <div>
          <div class="font-bold">Attention : {{ unaccountedCount }} équipement(s) non scanné(s)</div>
          <div class="text-amber-800 mt-0.5">
            Si vous clôturez maintenant sans marquer ces items comme manquants, ils resteront en reliquat hors-location et le dossier passera en Retour Partiel.
          </div>
        </div>
      </div>

      <!-- Itemized Breakdown -->
      <div class="space-y-2 max-h-60 overflow-y-auto pr-1">
        <div class="text-xs font-bold uppercase tracking-wider text-cortex-text-muted">
          Détail par équipement & statut
        </div>
        <div class="divide-y divide-cortex-border border border-cortex-border rounded-xl overflow-hidden">
          <div
            v-for="item in rental.items"
            :key="item.id"
            class="p-3 bg-cortex-surface flex items-center justify-between gap-4"
          >
            <div>
              <div class="text-xs font-bold text-cortex-text-primary">{{ item.item_name }}</div>
              <div class="text-[11px] font-mono text-cortex-text-muted">{{ item.item_code }} — Qté: {{ item.quantity }}</div>
              <div class="flex flex-wrap gap-1 mt-1">
                <span
                  v-for="sn in item.assigned_serials"
                  :key="sn"
                  class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold"
                  :class="getSerialBadgeClass(sn)"
                >
                  {{ sn }} — {{ getSerialStatusLabel(sn) }}
                </span>
              </div>
            </div>
            <div class="text-right shrink-0">
              <span class="text-xs font-mono font-bold text-cortex-text-secondary">
                {{ getItemReturnCount(item) }} / {{ item.quantity }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Operational Notice -->
      <div class="p-3 bg-cortex-surface-muted border border-cortex-border rounded-xl text-[11px] text-cortex-text-muted">
        ℹ️ <strong>Impact inventaire immédiat :</strong> La validation libère les unités conformes pour les prochaines réservations. Les anomalies génèrent des tickets d'inspection et sont immuablement inscrites dans l'Audit Log.
      </div>

      <!-- Actions Footer -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-cortex-border">
        <button
          type="button"
          class="px-4 py-2.5 rounded-xl border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-xs font-semibold text-cortex-text-secondary transition-colors min-h-[44px]"
          @click="$emit('close')"
        >
          Reprendre le contrôle
        </button>
        <button
          type="button"
          class="px-5 py-2.5 rounded-xl bg-cortex-primary hover:bg-cortex-primary-hover text-white text-xs font-bold shadow-sm transition-colors min-h-[44px] flex items-center gap-2 disabled:opacity-50"
          :disabled="isSubmitting"
          @click="$emit('confirm')"
        >
          <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
          <span>{{ unaccountedCount > 0 ? 'Enregistrer le Retour Partiel' : 'Clôturer Définitivement le Retour' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AlertTriangle, FileCheck, Loader2, X } from 'lucide-vue-next'
import type { RentalTransaction, RentalLineItem } from '@/api/contracts'

const props = defineProps<{
  rental: RentalTransaction
  missingSerials: string[]
  damagedSerials: string[]
  returnedSerials: string[]
  isOpen: boolean
  isSubmitting: boolean
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'confirm'): void
}>()

const totalExpected = computed(() => {
  return props.rental.items.reduce((sum, item) => sum + item.quantity, 0)
})

const unaccountedCount = computed(() => {
  const totalAccounted = props.returnedSerials.length + props.missingSerials.length
  return Math.max(0, totalExpected.value - totalAccounted)
})

function getItemReturnCount(item: RentalLineItem): number {
  return (item.assigned_serials || []).filter((sn: string) => 
    props.returnedSerials.includes(sn) || props.missingSerials.includes(sn)
  ).length
}

function getSerialStatusLabel(sn: string): string {
  if (props.damagedSerials.includes(sn)) return 'Endommagé'
  if (props.missingSerials.includes(sn)) return 'Manquant'
  if (props.returnedSerials.includes(sn)) return 'Retourné'
  return 'En attente'
}

function getSerialBadgeClass(sn: string): string {
  if (props.damagedSerials.includes(sn)) return 'bg-red-100 text-red-800 border border-red-200'
  if (props.missingSerials.includes(sn)) return 'bg-amber-100 text-amber-800 border border-amber-200'
  if (props.returnedSerials.includes(sn)) return 'bg-emerald-100 text-emerald-800 border border-emerald-200'
  return 'bg-slate-100 text-slate-700 border border-slate-200'
}
</script>
