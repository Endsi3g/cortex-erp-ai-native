<template>
  <div class="rounded-xl border border-red-200 bg-red-50/30 p-5 shadow-2xs" data-test="operations-attention-required">
    <div class="flex items-center justify-between pb-3 border-b border-red-200/60">
      <div class="flex items-center gap-2">
        <AlertTriangle class="w-5 h-5 text-red-600" />
        <h2 class="text-sm font-bold text-red-950">{{ t('operations.attention_title') }}</h2>
      </div>
      <span class="px-2 py-0.5 rounded bg-red-100 text-red-800 text-[11px] font-bold font-mono">
        3 alertes
      </span>
    </div>

    <div class="mt-3 space-y-3">
      <!-- 1. Expired Insurance -->
      <div class="p-3 rounded-lg border border-red-200 bg-cortex-surface shadow-2xs" data-test="alert-expired-insurance">
        <div class="flex items-center justify-between">
          <span class="px-1.5 py-0.5 rounded bg-red-100 text-red-800 text-[10px] font-bold uppercase">
            {{ t('operations.insurance_alert') }}
          </span>
          <span class="font-mono text-xs text-cortex-text-muted">DEMO-TRX-2026-003</span>
        </div>
        <p class="mt-1 text-xs font-semibold text-cortex-text-primary">Trequista Events — Festival Live Stream</p>
        <p class="text-[11px] text-cortex-text-muted mt-0.5">Police d'assurance expirée le 30 août. Bloque la confirmation en contrat.</p>
        <div class="mt-2 flex items-center justify-between">
          <RouterLink
            to="/app/cortex-rental/DEMO-TRX-2026-003"
            class="text-xs font-medium text-red-700 hover:text-red-900 underline underline-offset-2"
          >
            Examiner la soumission →
          </RouterLink>
          <RouterLink
            to="/app/cortex-approvals"
            class="text-[11px] px-2 py-1 rounded bg-red-50 text-red-800 border border-red-200 font-medium hover:bg-red-100"
          >
            Voir dérogation SAS
          </RouterLink>
        </div>
      </div>

      <!-- 2. Equipment in Quarantine -->
      <div class="p-3 rounded-lg border border-amber-200 bg-cortex-surface shadow-2xs" data-test="alert-quarantine">
        <div class="flex items-center justify-between">
          <span class="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-bold uppercase">
            {{ t('operations.quarantine_alert') }}
          </span>
          <span class="font-mono text-xs text-cortex-text-muted">DEMO-SN-ALX-004</span>
        </div>
        <p class="mt-1 text-xs font-semibold text-cortex-text-primary">ARRI Alexa 35 (#DEMO-SN-ALX-004)</p>
        <p class="text-[11px] text-cortex-text-muted mt-0.5">Poussière sur capteur signalée lors du retour DEMO-TRX-2026-004. Maintenance en cours.</p>
        <div class="mt-2 flex items-center justify-between">
          <span class="text-[11px] text-cortex-text-muted">Banc Service B</span>
          <RouterLink
            to="/app/cortex-serial/DEMO-SN-ALX-004"
            class="text-xs font-medium text-amber-700 hover:text-amber-900 underline underline-offset-2"
          >
            Fiche série →
          </RouterLink>
        </div>
      </div>

      <!-- 3. Overdue Return -->
      <div class="p-3 rounded-lg border border-amber-200 bg-cortex-surface shadow-2xs" data-test="alert-overdue-return">
        <div class="flex items-center justify-between">
          <span class="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-bold uppercase">
            {{ t('operations.overdue_alert') }}
          </span>
          <span class="font-mono text-xs text-cortex-text-muted">DEMO-TRX-2026-004</span>
        </div>
        <p class="mt-1 text-xs font-semibold text-cortex-text-primary">Production Nord — Reliquat non restitué</p>
        <p class="text-[11px] text-cortex-text-muted mt-0.5">1 adaptateur PL/LPL manquant au retour du 1er septembre.</p>
        <div class="mt-2 flex items-center justify-between">
          <RouterLink
            to="/app/cortex-checkin/DEMO-TRX-2026-004"
            class="text-xs font-medium text-amber-700 hover:text-amber-900 underline underline-offset-2"
          >
            Reprendre Check-in →
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { AlertTriangle } from 'lucide-vue-next'

const { t } = useI18n()
</script>
