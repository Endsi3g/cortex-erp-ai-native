<template>
  <!--
    Line chart matching the ERPNext reference: 324px block, 170px plot
    starting 60px below the summary rule, category points centred in their
    bands, horizontal #F4F5F6 grid only, 12px legend swatches every 150px.
  -->
  <figure class="relative h-[324px] w-full" :aria-label="t('finance.pnl.chart_label')">
    <ECharts :options="options" class="h-full w-full" />
    <div class="absolute left-[64px] top-[265px] flex" role="group" :aria-label="t('finance.pnl.legend')">
      <button
        v-for="serie in series"
        :key="serie.key"
        type="button"
        class="flex w-[150px] items-center gap-2.5 text-left text-lg leading-none text-[#313B44] outline-none focus-visible:underline"
        :class="hidden.has(serie.key) ? 'opacity-40' : ''"
        :aria-pressed="!hidden.has(serie.key)"
        @click="toggle(serie.key)"
      >
        <span class="size-3 shrink-0 rounded-[3px]" :style="{ backgroundColor: serie.color }" aria-hidden="true" />
        {{ serie.name }}
      </button>
    </div>
    <figcaption class="sr-only">{{ summary }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ECharts } from 'frappe-ui'
import type { EChartsOption } from 'echarts'
import type { PnlPeriod } from '@/api/contracts'
import { formatCompactNumber, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const props = defineProps<{ periods: PnlPeriod[]; currency: string | null }>()
const { t, locale } = useI18n()

const LABEL = '#313B44'
const COLORS = { income: '#E789AD', expense: '#4B88D2', profit: '#69B97A' }

const summary = computed(() =>
  props.periods
    .map(p => `${p.label}: ${t('finance.pnl.income')} ${formatMoney(p.income, props.currency, locale.value as LocaleType)}, ${t('finance.pnl.expense')} ${formatMoney(p.expense, props.currency, locale.value as LocaleType)}, ${t('finance.pnl.net_profit_loss')} ${formatMoney(p.profitLoss, props.currency, locale.value as LocaleType)}`)
    .join(' ; ')
)

/** Round the axis up to a "nice" maximum split into exactly 4 steps (0, 250 k, … 1 M). */
function niceAxis(values: number[]): { max: number; interval: number } | undefined {
  const top = Math.max(0, ...values)
  if (top <= 0) return undefined
  const raw = top / 4
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map(m => m * magnitude).find(candidate => candidate >= raw) ?? raw
  return { max: step * 4, interval: step }
}

const series = computed(() => [
  { key: 'income', name: t('finance.pnl.income'), color: COLORS.income, data: props.periods.map(p => p.income) },
  { key: 'expense', name: t('finance.pnl.expense'), color: COLORS.expense, data: props.periods.map(p => p.expense) },
  { key: 'profit', name: t('finance.pnl.net_profit_loss'), color: COLORS.profit, data: props.periods.map(p => p.profitLoss) }
])

// The legend is rendered in HTML (fixed 150px entries, keyboard reachable);
// ECharts keeps the visibility state through `legend.selected`.
const hidden = ref(new Set<string>())
function toggle(key: string) {
  const next = new Set(hidden.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  hidden.value = next
}

const options = computed<EChartsOption>(() => {
  const loc = locale.value as LocaleType
  return {
    animation: false,
    textStyle: { fontFamily: 'InterVariable, Inter, sans-serif' },
    grid: { top: 60, left: 62, right: 41, bottom: 94, containLabel: false },
    xAxis: {
      type: 'category',
      boundaryGap: true,
      data: props.periods.map(p => p.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: LABEL, fontSize: 11, margin: 10.5 }
    },
    yAxis: {
      type: 'value',
      splitNumber: 4,
      min: 0,
      ...niceAxis(props.periods.flatMap(p => [p.income, p.expense, p.profitLoss])),
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F4F5F6', width: 1 } },
      axisLabel: { color: LABEL, fontSize: 11, margin: 10, formatter: (value: number) => formatCompactNumber(value, loc) }
    },
    legend: {
      show: false,
      selected: Object.fromEntries(series.value.map(serie => [serie.name, !hidden.value.has(serie.key)]))
    },
    tooltip: {
      trigger: 'axis',
      valueFormatter: value => formatMoney(Number(value), props.currency, loc)
    },
    series: series.value.map(s => ({
      name: s.name,
      type: 'line',
      data: s.data,
      symbol: 'none',
      smooth: false,
      lineStyle: { width: 2, color: s.color },
      itemStyle: { color: s.color }
    }))
  }
})
</script>
