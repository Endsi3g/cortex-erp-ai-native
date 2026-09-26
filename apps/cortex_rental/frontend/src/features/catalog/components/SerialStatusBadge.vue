<template>
  <Badge :theme="theme" variant="subtle" :size="size">{{ t(`catalog.serial_status.${status.replace(/ /g, '_')}`) }}</Badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from 'frappe-ui'
import type { SerialStatus } from '@/api/contracts/catalog'

const props = withDefaults(defineProps<{ status: SerialStatus; size?: 'sm' | 'md' }>(), { size: 'sm' })
const { t } = useI18n()
const THEMES: Record<SerialStatus, string> = { Active: 'green', Quarantine: 'orange', 'Under Repair': 'orange', Missing: 'red', Decommissioned: 'gray' }
const theme = computed(() => THEMES[props.status] ?? 'gray')
</script>
