<template>
  <Badge :theme="theme" variant="subtle">{{ t(`consignment_screen.status_${status}`) }}</Badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from 'frappe-ui'
import type { StatementStatus } from '@/api/contracts'

const props = defineProps<{ status: StatementStatus }>()
const { t } = useI18n()
const theme = computed(() => ({ not_prepared: 'gray', draft: 'orange', approved: 'blue', paid: 'green' } as const)[props.status] ?? 'gray')
</script>
