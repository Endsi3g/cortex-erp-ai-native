<template>
  <dl class="cx-kpis" data-test="kpi-strip">
    <template v-for="(item, index) in items" :key="item.key">
      <span v-if="operators && index > 0" class="cx-kpi-op" aria-hidden="true">{{ operators[index - 1] }}</span>
      <div class="cx-kpi">
        <dt class="cx-kpi__label">{{ item.label }}</dt>
        <dd class="m-0">
          <button
            v-if="item.selectable"
            type="button"
            class="cx-kpi__value"
            :aria-pressed="item.pressed === true"
            @click="$emit('select', item.key)"
          >{{ item.value }}</button>
          <RouterLink v-else-if="item.to" :to="item.to" class="cx-kpi__value">{{ item.value }}</RouterLink>
          <span v-else class="cx-kpi__value" :class="{ 'cx-kpi__value--positive': item.positive }" :title="item.hint">{{ item.value }}</span>
          <div v-if="item.detail" class="cx-kpi__detail">{{ item.detail }}</div>
        </dd>
      </div>
    </template>
  </dl>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'

export interface KpiItem {
  key: string
  label: string
  value: string
  detail?: string
  hint?: string
  to?: RouteLocationRaw
  selectable?: boolean
  pressed?: boolean
  positive?: boolean
}

defineProps<{ items: KpiItem[]; operators?: string[] }>()
defineEmits<{ (e: 'select', key: string): void }>()
</script>
