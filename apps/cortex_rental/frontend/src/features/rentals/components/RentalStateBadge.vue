<template>
  <Badge :theme="theme" variant="subtle" :size="size">{{ t(`rental_states.${state}`) }}</Badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from 'frappe-ui'
import type { RentalStateValue } from '@/api/contracts/rentals'

const props = withDefaults(defineProps<{ state: RentalStateValue; size?: 'sm' | 'md' | 'lg' }>(), { size: 'sm' })
const { t } = useI18n()

// One colour per lifecycle stage, reused on every screen.
const THEMES: Record<RentalStateValue, string> = {
  Quote: 'gray',
  Reservation: 'blue',
  Contract: 'blue',
  'Checked Out': 'orange',
  Returned: 'green',
  Closed: 'gray',
  Cancelled: 'red',
  Disputed: 'red',
  Quarantine: 'orange'
}
const theme = computed(() => THEMES[props.state] ?? 'gray')
</script>
