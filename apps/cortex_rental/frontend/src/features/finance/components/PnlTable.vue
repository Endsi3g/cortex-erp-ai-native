<template>
  <!--
    ERPNext report grid (inspiration/image.png): 35px #F3F3F3 header,
    filter row, 33px body rows with #EDEDED rules, 37px row-number column,
    300px account column, 150px period columns; 20px indent per level,
    9×5 chevrons, depth-0 groups in bold.
  -->
  <div class="w-full overflow-x-auto">
    <table class="w-max min-w-full border-collapse border-t border-outline-gray-1 text-base text-ink-gray-8" :aria-label="t('finance.pnl.table_label')">
      <colgroup>
        <col class="w-[37px]" />
        <col class="w-[300px]" />
        <col v-for="period in periods" :key="period.key" class="w-[150px]" />
        <col />
      </colgroup>
      <thead>
        <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
          <th scope="col" class="border-r border-outline-gray-1 font-normal"><span class="sr-only">#</span></th>
          <th scope="col" class="border-r border-outline-gray-1 px-[7.5px] text-left font-normal">{{ t('finance.pnl.account') }}</th>
          <th v-for="period in periods" :key="period.key" scope="col" class="border-r border-outline-gray-1 px-[7.5px] text-right font-normal">
            {{ period.label }}
          </th>
          <th aria-hidden="true" />
        </tr>
        <tr class="h-[35px] border-b border-outline-gray-1">
          <td class="border-r border-outline-gray-1 px-[7px]"><span class="block h-[18px] rounded bg-surface-gray-2" /></td>
          <td class="border-r border-outline-gray-1 px-[7px]">
            <input
              v-model="accountFilter"
              type="search"
              class="block h-[18px] w-full rounded border-0 bg-surface-gray-2 px-1.5 text-sm text-ink-gray-8 placeholder-ink-gray-4 focus:ring-1 focus:ring-outline-gray-3"
              :aria-label="t('finance.pnl.filter_account')"
            />
          </td>
          <td v-for="period in periods" :key="period.key" class="border-r border-outline-gray-1 px-[7px]">
            <input
              v-model="periodFilters[period.key]"
              type="search"
              class="block h-[18px] w-full rounded border-0 bg-surface-gray-2 px-1.5 text-right text-sm text-ink-gray-8 placeholder-ink-gray-4 focus:ring-1 focus:ring-outline-gray-3"
              :aria-label="t('finance.pnl.filter_period', { period: period.label })"
            />
          </td>
          <td aria-hidden="true" />
        </tr>
      </thead>
      <tbody>
        <tr v-if="!visibleRows.length" class="h-[33px]">
          <td :colspan="periods.length + 3" class="px-4 py-6 text-center text-ink-gray-5">{{ t('finance.pnl.no_rows') }}</td>
        </tr>
        <tr
          v-for="(entry, index) in visibleRows"
          :key="entry.row.id"
          class="h-[33px] border-b border-outline-gray-1 hover:bg-surface-gray-1"
          :class="entry.row.depth === 0 ? 'font-semibold' : ''"
        >
          <td class="border-r border-outline-gray-1 text-center font-normal tabular-nums text-ink-gray-8">{{ index + 1 }}</td>
          <td class="border-r border-outline-gray-1 pr-[7.5px]">
            <div class="flex items-center" :style="{ paddingLeft: `${indent(entry.row)}px` }">
              <button
                v-if="entry.row.children.length"
                type="button"
                class="mr-2 flex size-[9px] shrink-0 items-center justify-center text-ink-gray-8"
                :aria-expanded="!collapsed.has(entry.row.id)"
                :aria-label="collapsed.has(entry.row.id) ? t('finance.pnl.expand', { name: entry.row.name }) : t('finance.pnl.collapse', { name: entry.row.name })"
                @click="toggle(entry.row.id)"
              >
                <svg width="9" height="5" viewBox="0 0 9 5" aria-hidden="true" :class="collapsed.has(entry.row.id) ? '-rotate-90' : ''">
                  <path d="M0.75 0.75 4.5 4.25 8.25 0.75" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>
              <button
                type="button"
                class="truncate text-left hover:underline focus-visible:underline focus-visible:outline-none"
                :title="t('finance.pnl.open_ledger', { name: entry.row.name })"
                @click="$emit('open-ledger', entry.row)"
              >
                {{ entry.row.name }}
              </button>
            </div>
          </td>
          <td
            v-for="period in periods"
            :key="period.key"
            class="border-r border-outline-gray-1 px-[7.5px] text-right tabular-nums"
          >
            {{ money(entry.row.values[period.key]) }}
          </td>
          <td aria-hidden="true" />
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PnlAccountRow, PnlPeriod } from '@/api/contracts'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const props = defineProps<{ accounts: PnlAccountRow[]; periods: PnlPeriod[]; currency: string | null }>()
defineEmits<{ 'open-ledger': [row: PnlAccountRow] }>()

const { t, locale } = useI18n()
const collapsed = ref(new Set<string>())
const accountFilter = ref('')
const periodFilters = reactive<Record<string, string>>({})

// Measured on the reference: a group's chevron sits 10.5px into the cell plus
// 20px per level; a leaf's label lines up with its parent's label (17px past
// the parent's chevron).
function indent(row: PnlAccountRow): number {
  if (row.children.length || row.depth === 0) return 10.5 + row.depth * 20
  return 7.5 + row.depth * 20
}

function money(value: number | null | undefined): string {
  return formatMoney(value ?? 0, props.currency, locale.value as LocaleType)
}

function toggle(id: string) {
  const next = new Set(collapsed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsed.value = next
}

function matchesAmount(value: number | null | undefined, filter: string): boolean {
  const query = filter.trim()
  if (!query) return true
  const numeric = Number(query.replace(/^[<>=]+/, '').replace(/\s/g, '').replace(',', '.'))
  const amount = value ?? 0
  if (/^>=/.test(query)) return amount >= numeric
  if (/^<=/.test(query)) return amount <= numeric
  if (/^>/.test(query)) return amount > numeric
  if (/^</.test(query)) return amount < numeric
  if (/^=/.test(query)) return amount === numeric
  return money(amount).toLowerCase().includes(query.toLowerCase())
}

function rowMatches(row: PnlAccountRow): boolean {
  const name = accountFilter.value.trim().toLowerCase()
  if (name && !row.name.toLowerCase().includes(name)) return false
  return props.periods.every(period => matchesAmount(row.values[period.key], periodFilters[period.key] ?? ''))
}

const filtering = computed(() => Boolean(accountFilter.value.trim()) || Object.values(periodFilters).some(value => value.trim()))

/** Depth-first flattening. While filtering, a row is kept if it or a descendant matches (ancestors give context). */
const visibleRows = computed(() => {
  const out: Array<{ row: PnlAccountRow }> = []
  const walk = (rows: PnlAccountRow[]): boolean => {
    let any = false
    for (const row of rows) {
      const start = out.length
      out.push({ row })
      const childMatch = !collapsed.value.has(row.id) || filtering.value ? walk(row.children) : false
      const keep = !filtering.value || rowMatches(row) || childMatch
      if (!keep) out.splice(start)
      any = any || keep
    }
    return any
  }
  walk(props.accounts)
  return out
})
</script>
