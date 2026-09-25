<script setup lang="ts">
import { computed } from 'vue';
import CortexIcon from '../../icons/CortexIcon.vue';

export interface TableColumn {
  key: string;
  label: string;
  align?: 'left' | 'center' | 'right';
  width?: string;
  sortable?: boolean;
  isMono?: boolean;
}

interface Props {
  columns: TableColumn[];
  rows: Record<string, any>[];
  rowKey?: string;
  striped?: boolean;
  compact?: boolean;
  stickyHeader?: boolean;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  loading?: boolean;
  emptyText?: string;
  locale?: 'fr-CA' | 'en-CA';
}

const props = withDefaults(defineProps<Props>(), {
  rowKey: 'id',
  striped: true,
  compact: false,
  stickyHeader: true,
  sortBy: undefined,
  sortOrder: 'asc',
  loading: false,
  emptyText: undefined,
  locale: 'fr-CA',
});

const emit = defineEmits<{
  (e: 'sort', columnKey: string, nextOrder: 'asc' | 'desc'): void;
  (e: 'row-click', row: Record<string, any>, index: number): void;
}>();

const resolvedEmptyText = computed(() => {
  if (props.emptyText) return props.emptyText;
  return props.locale === 'en-CA' ? 'No data available' : 'Aucune donnée disponible';
});

function handleHeaderClick(col: TableColumn) {
  if (!col.sortable) return;
  const nextOrder = props.sortBy === col.key && props.sortOrder === 'asc' ? 'desc' : 'asc';
  emit('sort', col.key, nextOrder);
}
</script>

<template>
  <div
    :class="[
      'cx-table-container',
      { 'cx-table-container--sticky': stickyHeader },
    ]"
  >
    <table
      :class="[
        'cx-table',
        {
          'cx-table--striped': striped,
          'cx-table--compact': compact,
        },
      ]"
    >
      <thead class="cx-table__head">
        <tr class="cx-table__head-row">
          <th
            v-for="col in columns"
            :key="col.key"
            scope="col"
            :style="{ width: col.width, textAlign: col.align || 'left' }"
            :class="[
              'cx-table__th',
              { 'cx-table__th--sortable': col.sortable },
            ]"
            :aria-sort="
              sortBy === col.key
                ? sortOrder === 'asc'
                  ? 'ascending'
                  : 'descending'
                : undefined
            "
            @click="handleHeaderClick(col)"
          >
            <div class="cx-table__th-content" :style="{ justifyContent: col.align === 'right' ? 'flex-end' : col.align === 'center' ? 'center' : 'flex-start' }">
              <span>{{ col.label }}</span>
              <span v-if="col.sortable" class="cx-table__sort-icon">
                <CortexIcon
                  v-if="sortBy === col.key"
                  :name="sortOrder === 'asc' ? 'chevron-up' : 'chevron-down'"
                  :size="13"
                  color="var(--cortex-green-600, #087a43)"
                />
                <CortexIcon
                  v-else
                  name="chevron-down"
                  :size="12"
                  color="var(--cortex-text-disabled, #6d9685)"
                />
              </span>
            </div>
          </th>
        </tr>
      </thead>

      <tbody class="cx-table__body">
        <!-- Loading rows skeleton -->
        <tr v-if="loading" v-for="n in 4" :key="`loading-${n}`" class="cx-table__loading-row">
          <td v-for="col in columns" :key="col.key" class="cx-table__td">
            <div class="cx-table__skeleton-cell" />
          </td>
        </tr>

        <!-- Data rows -->
        <tr
          v-else-if="rows.length > 0"
          v-for="(row, idx) in rows"
          :key="row[rowKey] || idx"
          class="cx-table__row"
          @click="emit('row-click', row, idx)"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            :style="{ textAlign: col.align || 'left' }"
            :class="[
              'cx-table__td',
              { 'cx-table__td--mono': col.isMono || col.align === 'right' },
            ]"
          >
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]" :index="idx">
              {{ row[col.key] }}
            </slot>
          </td>
        </tr>

        <!-- Empty state -->
        <tr v-else class="cx-table__empty-row">
          <td :colspan="columns.length" class="cx-table__empty-td">
            <slot name="empty">
              <div class="cx-table__empty-state">
                <CortexIcon name="archive" :size="24" color="var(--cortex-text-muted, #436354)" />
                <p>{{ resolvedEmptyText }}</p>
              </div>
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.cx-table-container {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--cortex-border, #cbdcd2);
  border-radius: var(--radius-md, 8px);
  background-color: var(--cortex-surface, #ffffff);
  box-sizing: border-box;
}

.cx-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-sans, Inter, sans-serif);
  font-size: 13px;
  color: var(--cortex-text, #08120d);
  text-align: left;
}

.cx-table__head {
  background-color: var(--cortex-surface-subtle, #f1f5f9);
  border-bottom: 1px solid var(--cortex-border, #cbdcd2);
}

.cx-table-container--sticky .cx-table__head {
  position: sticky;
  top: 0;
  z-index: 10;
}

.cx-table__th {
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--cortex-text-muted, #436354);
  white-space: nowrap;
}

.cx-table__th--sortable {
  cursor: pointer;
  user-select: none;
}

.cx-table__th--sortable:hover {
  color: var(--cortex-text, #08120d);
  background-color: var(--cortex-surface-hover, #e3ece6);
}

.cx-table__th-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cx-table__body .cx-table__row {
  border-bottom: 1px solid var(--cortex-border, #cbdcd2);
  transition: background-color var(--motion-fast, 120ms ease);
}

.cx-table__body .cx-table__row:last-child {
  border-bottom: none;
}

.cx-table__body .cx-table__row:hover {
  background-color: var(--cortex-surface-hover, #e3ece6);
}

.cx-table--striped .cx-table__body .cx-table__row:nth-child(even) {
  background-color: rgba(242, 247, 244, 0.4);
}

.cx-table__td {
  padding: 12px 14px;
  font-size: 13px;
  color: var(--cortex-text-secondary, #264034);
  vertical-align: middle;
}

.cx-table--compact .cx-table__th {
  padding: 6px 10px;
  font-size: 11.5px;
}

.cx-table--compact .cx-table__td {
  padding: 7px 10px;
  font-size: 12.5px;
}

.cx-table__td--mono {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-variant-numeric: tabular-nums lining-nums;
  font-size: 12.5px;
}

.cx-table__skeleton-cell {
  height: 16px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: cx-shimmer 1.5s infinite;
  border-radius: 4px;
}

.cx-table__empty-td {
  padding: 32px 16px;
  text-align: center;
}

.cx-table__empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--cortex-text-muted, #436354);
}

@keyframes cx-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
