<template>
  <!--
    ERPNext report/list grid, same measurements as the P&L reference:
    35px #F3F3F3 header, optional 35px filter row, 33px rows with #EDEDED
    rules, 37px row-number column. Columns render through `cell-<key>`
    slots when a screen needs links or badges.
  -->
  <div class="w-full">
    <div class="w-full overflow-x-auto">
      <table class="w-full min-w-max border-collapse border-t border-outline-gray-1 text-base text-ink-gray-8" :aria-label="label" :aria-busy="loading">
        <colgroup>
          <col class="w-[37px]" />
          <col v-for="column in columns" :key="column.key" :style="column.width ? { width: column.width } : undefined" />
        </colgroup>
        <thead>
          <tr class="h-[35px] border-b border-outline-gray-1 bg-surface-gray-2 text-ink-gray-6">
            <th scope="col" class="border-r border-outline-gray-1 font-normal"><span class="sr-only">#</span></th>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              class="whitespace-nowrap border-r border-outline-gray-1 px-[7.5px] font-normal last:border-r-0"
              :class="alignClass(column)"
              :aria-sort="sortKey === column.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined"
            >
              <button
                v-if="column.sortable !== false"
                type="button"
                class="inline-flex items-center gap-1 hover:text-ink-gray-8"
                @click="toggleSort(column.key)"
              >
                {{ column.label }}
                <span v-if="sortKey === column.key" aria-hidden="true">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </button>
              <template v-else>{{ column.label }}</template>
            </th>
          </tr>
          <tr v-if="filterRow" class="h-[35px] border-b border-outline-gray-1">
            <td class="border-r border-outline-gray-1 px-[7px]"><span class="block h-[18px] rounded bg-surface-gray-2" /></td>
            <td v-for="column in columns" :key="column.key" class="border-r border-outline-gray-1 px-[7px] last:border-r-0">
              <input
                v-model="columnFilters[column.key]"
                type="search"
                class="block h-[18px] w-full rounded border-0 bg-surface-gray-2 px-1.5 text-sm text-ink-gray-8 focus:ring-1 focus:ring-outline-gray-3"
                :class="column.align === 'right' ? 'text-right' : ''"
                :aria-label="t('table.filter_column', { column: column.label })"
              />
            </td>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && !rows.length" class="h-[33px]">
            <td :colspan="columns.length + 1" class="px-4 py-6 text-center text-ink-gray-5" role="status">{{ t('table.loading') }}</td>
          </tr>
          <tr v-else-if="!visibleRows.length" class="h-[33px]">
            <td :colspan="columns.length + 1" class="px-4 py-8 text-center text-ink-gray-5">{{ emptyText || t('table.empty') }}</td>
          </tr>
          <tr
            v-for="(row, index) in visibleRows"
            :key="String(row[rowKey])"
            class="h-[33px] border-b border-outline-gray-1 hover:bg-surface-gray-1"
            :class="clickable ? 'cursor-pointer' : ''"
            :tabindex="clickable ? 0 : undefined"
            @click="clickable && $emit('row-click', row)"
            @keydown.enter="clickable && $emit('row-click', row)"
          >
            <td class="border-r border-outline-gray-1 text-center tabular-nums">{{ offset + index + 1 }}</td>
            <td
              v-for="column in columns"
              :key="column.key"
              class="max-w-[420px] truncate border-r border-outline-gray-1 px-[7.5px] last:border-r-0"
              :class="[alignClass(column), column.align === 'right' ? 'tabular-nums' : '']"
            >
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">{{ display(column, row) }}</slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="total !== undefined" class="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div class="flex items-center gap-1" role="group" :aria-label="t('table.page_size')">
        <Button
          v-for="size in pageSizes"
          :key="size"
          size="sm"
          :variant="size === pageSize ? 'subtle' : 'ghost'"
          :aria-pressed="size === pageSize"
          @click="$emit('update:pageSize', size)"
        >
          {{ size }}
        </Button>
      </div>
      <div class="flex items-center gap-2 text-base text-ink-gray-6">
        <span>{{ t('table.range', { from: total ? offset + 1 : 0, to: Math.min(offset + rows.length, total), total }) }}</span>
        <Button size="sm" variant="ghost" :disabled="page <= 1" :aria-label="t('table.previous')" @click="$emit('update:page', page - 1)">‹</Button>
        <Button size="sm" variant="ghost" :disabled="offset + rows.length >= total" :aria-label="t('table.next')" @click="$emit('update:page', page + 1)">›</Button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts" generic="Row extends Record<string, unknown>">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from 'frappe-ui'

export interface DataTableColumn<R> {
  key: string
  label: string
  width?: string
  align?: 'left' | 'right' | 'center'
  sortable?: boolean
  format?: (row: R) => string
}

const props = withDefaults(defineProps<{
  label: string
  columns: DataTableColumn<Row>[]
  rows: Row[]
  rowKey?: string
  loading?: boolean
  emptyText?: string
  clickable?: boolean
  filterRow?: boolean
  total?: number
  page?: number
  pageSize?: number
  pageSizes?: number[]
}>(), {
  rowKey: 'name',
  loading: false,
  emptyText: '',
  clickable: false,
  filterRow: true,
  total: undefined,
  page: 1,
  pageSize: 20,
  pageSizes: () => [20, 100, 500]
})

defineEmits<{
  'row-click': [row: Row]
  'update:page': [page: number]
  'update:pageSize': [size: number]
}>()

const { t } = useI18n()
const columnFilters = reactive<Record<string, string>>({})
const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')

const offset = computed(() => (props.total !== undefined ? (props.page - 1) * props.pageSize : 0))

function alignClass(column: DataTableColumn<Row>) {
  return column.align === 'right' ? 'text-right' : column.align === 'center' ? 'text-center' : 'text-left'
}

function display(column: DataTableColumn<Row>, row: Row): string {
  if (column.format) return column.format(row)
  const value = row[column.key]
  return value === null || value === undefined ? '' : String(value)
}

function toggleSort(key: string) {
  if (sortKey.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

/** Client-side refinement of the rows already loaded (the server does paging and the main filters). */
const visibleRows = computed(() => {
  const active = props.columns.filter(column => (columnFilters[column.key] ?? '').trim())
  let rows = props.rows.filter(row =>
    active.every(column => display(column, row).toLowerCase().includes(columnFilters[column.key].trim().toLowerCase()))
  )
  if (sortKey.value) {
    const key = sortKey.value
    const dir = sortDir.value === 'asc' ? 1 : -1
    rows = [...rows].sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir
      return String(av ?? '').localeCompare(String(bv ?? ''), undefined, { numeric: true }) * dir
    })
  }
  return rows
})
</script>
