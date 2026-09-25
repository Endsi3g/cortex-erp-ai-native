<template>
  <Badge :theme="theme" variant="subtle">{{ label }}</Badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from 'frappe-ui'
import type { InsuranceStatus } from '@/api/contracts'
import { formatDate } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const props = defineProps<{ status: InsuranceStatus; validUntil: string | null }>()
const { t, locale } = useI18n()
const theme = computed(() => ({ valid: 'green', expired: 'red', unknown: 'gray' } as const)[props.status])
const label = computed(() =>
  props.status === 'unknown' ? t('customers.insurance_unknown') : t(`customers.insurance_${props.status}`, { date: formatDate(props.validUntil ?? '', locale.value as LocaleType) })
)
</script>
