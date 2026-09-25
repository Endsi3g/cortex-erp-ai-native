<template>
  <div class="rounded-xl border border-cortex-border bg-cortex-surface overflow-hidden">
    <div class="px-4 py-3 bg-cortex-surface-muted border-b border-cortex-border flex items-center justify-between">
      <span class="text-xs font-bold uppercase tracking-wider text-cortex-text-primary flex items-center gap-1.5">
        <GitCompare class="w-4 h-4 text-cortex-primary" />
        {{ $t('approvals.diff_title', 'Diff Comparatif — Avant / Après') }}
      </span>
      <span class="text-[11px] font-mono text-cortex-text-muted">
        {{ diffEntries.length }} champ(s) modifié(s)
      </span>
    </div>

    <div v-if="diffEntries.length === 0" class="p-6 text-center text-xs text-cortex-text-muted">
      Aucune mutation d'état détectée.
    </div>

    <div v-else class="divide-y divide-cortex-border">
      <div
        v-for="entry in diffEntries"
        :key="entry.field"
        class="p-3.5 grid grid-cols-1 md:grid-cols-12 gap-3 items-center text-xs hover:bg-cortex-surface-muted/30 transition-colors"
      >
        <!-- Field Name -->
        <div class="md:col-span-4 font-mono font-bold text-cortex-text-primary flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-cortex-primary"></span>
          <span>{{ entry.field }}</span>
        </div>

        <!-- Before State -->
        <div class="md:col-span-3 p-2 rounded-lg bg-red-50/70 border border-red-200 text-red-900 font-mono text-[11px] break-all">
          <span class="text-[9px] uppercase font-bold text-red-500 block mb-0.5">Avant</span>
          <span>{{ formatValue(entry.oldValue) }}</span>
        </div>

        <!-- Arrow Indicator -->
        <div class="md:col-span-1 flex justify-center text-cortex-text-muted">
          <ArrowRight class="w-4 h-4" />
        </div>

        <!-- After State -->
        <div class="md:col-span-4 p-2 rounded-lg bg-emerald-50/70 border border-emerald-200 text-emerald-900 font-mono text-[11px] font-semibold break-all">
          <span class="text-[9px] uppercase font-bold text-emerald-600 block mb-0.5">Après (Proposé)</span>
          <span>{{ formatValue(entry.newValue) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight, GitCompare } from 'lucide-vue-next'
import { computeObjectDiff, type DiffEntry } from '@/utils/audit'

const props = defineProps<{
  beforeState?: Record<string, unknown>
  afterState?: Record<string, unknown>
}>()

const diffEntries = computed<DiffEntry[]>(() => {
  return computeObjectDiff(props.beforeState || {}, props.afterState || {})
})

function formatValue(val: unknown): string {
  if (val === undefined) return 'undefined'
  if (val === null) return 'null'
  if (typeof val === 'boolean') return val ? 'true' : 'false'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}
</script>
