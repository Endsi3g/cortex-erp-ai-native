<template>
  <!-- Data a tool read from Cortex, with a way to the real page. -->
  <section class="overflow-hidden rounded-xl border border-[var(--cl-border)] bg-white font-sans" :aria-label="model.title">
    <header class="flex items-center gap-2.5 px-4 pb-2 pt-3">
      <span class="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[var(--cl-bubble)] text-[var(--cl-muted)]">
        <component :is="ICONS[model.icon]" class="size-4" :stroke-width="1.75" aria-hidden="true" />
      </span>
      <div class="min-w-0 flex-1">
        <h3 class="truncate text-[14px] font-medium text-[var(--cl-text)]">{{ model.title }}</h3>
        <p v-if="model.subtitle" class="truncate text-[12px] text-[var(--cl-muted)]">{{ model.subtitle }}</p>
      </div>
    </header>

    <div v-if="model.tiles?.length" class="grid grid-cols-2 gap-px border-t border-[var(--cl-border)] bg-[var(--cl-border)] sm:grid-cols-4">
      <div v-for="tile in model.tiles" :key="tile.label" class="bg-white px-4 py-3">
        <p class="text-[12px] text-[var(--cl-muted)]">{{ tile.label }}</p>
        <p class="mt-0.5 text-[18px] font-semibold tabular-nums" :class="TONE[tile.tone ?? 'none']">{{ tile.value }}</p>
      </div>
    </div>

    <dl v-if="model.fields?.length" class="grid grid-cols-1 gap-x-6 gap-y-2 border-t border-[var(--cl-border)] px-4 py-3 sm:grid-cols-2">
      <div v-for="field in model.fields" :key="field.label" class="flex items-baseline justify-between gap-3 text-[13px]">
        <dt class="text-[var(--cl-muted)]">{{ field.label }}</dt>
        <dd class="text-right tabular-nums" :class="TONE[field.value.tone ?? 'none']">{{ field.value.text }}</dd>
      </div>
    </dl>

    <div v-if="model.columns && model.rows" class="max-h-[320px] overflow-auto border-t border-[var(--cl-border)]">
      <table class="w-full border-collapse text-[13px]">
        <thead class="sticky top-0 bg-[var(--cl-panel)] text-[var(--cl-muted)]">
          <tr>
            <th v-for="column in model.columns" :key="column.label" scope="col" class="whitespace-nowrap px-3 py-1.5 font-normal" :class="column.align === 'right' ? 'text-right' : 'text-left'">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!model.rows.length"><td :colspan="model.columns.length" class="px-3 py-3 text-[var(--cl-muted)]">{{ t('ai.widget.empty') }}</td></tr>
          <tr
            v-for="(row, index) in model.rows"
            :key="index"
            class="border-t border-[var(--cl-border)]"
            :class="row.route ? 'cursor-pointer hover:bg-[var(--cl-bg)]' : ''"
            :tabindex="row.route ? 0 : undefined"
            @click="row.route && $emit('open', row.route, model.title)"
            @keydown.enter="row.route && $emit('open', row.route, model.title)"
          >
            <td v-for="(cell, cellIndex) in row.cells" :key="cellIndex" class="max-w-[260px] truncate px-3 py-1.5" :class="[cell.align === 'right' ? 'text-right tabular-nums' : '', cell.mono ? 'font-mono text-[12px]' : '', TONE[cell.tone ?? 'none']]">{{ cell.text }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <dl v-if="model.footer?.length" class="space-y-1 border-t border-[var(--cl-border)] px-4 py-2.5 text-[13px]">
      <div v-for="line in model.footer" :key="line.label" class="flex justify-between" :class="line.strong ? 'font-semibold text-[var(--cl-text)]' : 'text-[var(--cl-muted)]'">
        <dt>{{ line.label }}</dt><dd class="tabular-nums">{{ line.value }}</dd>
      </div>
    </dl>

    <footer class="flex flex-wrap items-center gap-1 border-t border-[var(--cl-border)] bg-[var(--cl-bg)] px-2 py-1.5">
      <button v-if="canPreview" type="button" class="flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] text-[var(--cl-text)] hover:bg-[var(--cl-bubble)]" @click="$emit('open', model.route, model.title)">
        <PanelRight class="size-3.5" :stroke-width="1.75" aria-hidden="true" />{{ t('ai.widget.open_here') }}
      </button>
      <RouterLink :to="model.route" class="flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] text-[var(--cl-text)] hover:bg-[var(--cl-bubble)]">
        <ArrowUpRight class="size-3.5" :stroke-width="1.75" aria-hidden="true" />{{ model.routeLabel }}
      </RouterLink>
      <RouterLink v-if="model.action" :to="model.action.route" class="ml-auto flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] font-medium text-[var(--cl-accent-hover)] hover:bg-[var(--cl-bubble)]">
        <FilePlus2 class="size-3.5" :stroke-width="1.75" aria-hidden="true" />{{ model.action.label }}
      </RouterLink>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ArrowUpRight, CalendarRange, ChartLine, FilePlus2, FileText, LayoutGrid, PanelRight, Receipt, Table2 } from 'lucide-vue-next'
import type { WidgetModel } from '../widgets'

defineProps<{ model: WidgetModel; canPreview?: boolean }>()
defineEmits<{ open: [route: string, title: string] }>()
const { t } = useI18n()

const ICONS = { table: Table2, record: FileText, kpis: LayoutGrid, availability: CalendarRange, pricing: Receipt, report: ChartLine }
const TONE: Record<string, string> = { none: 'text-[var(--cl-text)]', green: 'text-ink-green-3', red: 'text-ink-red-4', orange: 'text-ink-amber-3', gray: 'text-[var(--cl-muted)]' }
</script>
