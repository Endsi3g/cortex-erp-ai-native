<template>
  <!--
    ERPNext report summary (inspiration/image.png): three figures on a
    regular 243px pitch at 1370px, joined by "−" and "=" operator boxes
    (24×39, #E2E2E2 border), 27px vertical padding, 1px bottom rule.
    Column gap is a percentage of the row so the pitch scales with width.
  -->
  <section
    class="mx-6 mt-[35px] flex flex-wrap items-center justify-center gap-x-[9.9%] gap-y-4 border-b border-outline-gray-1 pb-[28.5px] pt-[27px]"
    :aria-label="t('finance.pnl.summary')"
  >
    <div class="w-[200px] text-center">
      <p class="text-base text-ink-gray-6">{{ t('finance.pnl.total_income') }}</p>
      <p class="mt-2 text-2xl font-semibold tabular-nums text-ink-gray-8">{{ money(totalIncome) }}</p>
    </div>
    <span class="flex h-[39px] w-6 items-center justify-center rounded border border-outline-gray-2 text-lg text-ink-gray-6" aria-hidden="true">−</span>
    <div class="w-[200px] text-center">
      <p class="text-base text-ink-gray-6">{{ t('finance.pnl.total_expense') }}</p>
      <p class="mt-2 text-2xl font-semibold tabular-nums text-ink-gray-8">{{ money(totalExpense) }}</p>
    </div>
    <span class="flex h-[39px] w-6 items-center justify-center rounded border border-outline-gray-2 text-lg text-ink-blue-3" aria-hidden="true">=</span>
    <div class="w-[200px] text-center">
      <p class="text-base text-ink-gray-6">{{ netProfit !== null && netProfit < 0 ? t('finance.pnl.net_loss') : t('finance.pnl.net_profit') }}</p>
      <p
        class="mt-2 text-2xl font-semibold tabular-nums"
        :class="netProfit !== null && netProfit < 0 ? 'text-ink-red-4' : 'text-report-profit-text'"
      >
        {{ money(netProfit) }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const props = defineProps<{
  totalIncome: number | null
  totalExpense: number | null
  netProfit: number | null
  currency: string | null
}>()

const { t, locale } = useI18n()

function money(value: number | null): string {
  return formatMoney(value, props.currency, locale.value as LocaleType)
}
</script>
