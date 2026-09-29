<template>
  <div>
    <button v-if="rental.rental_state === 'Quote'" type="button" class="cx-btn-primary" :disabled="isActionLoading" data-test="cta-confirm-reservation" @click="emit('action', 'requestReservation')">
      {{ t('rental_detail.next_action_quote') }}
    </button>
    <button v-else-if="rental.rental_state === 'Reservation'" type="button" class="cx-btn-primary" :disabled="isActionLoading" data-test="cta-request-contract" @click="emit('action', 'requestContract')">
      {{ t('rental_detail.next_action_reservation') }}
    </button>
    <RouterLink v-else-if="rental.rental_state === 'Contract'" :to="`/app/cortex-checkout/${rental.name}`" class="cx-btn-primary" data-test="cta-start-checkout">
      {{ t('rental_detail.next_action_contract') }}
    </RouterLink>
    <RouterLink v-else-if="rental.rental_state === 'Checked Out'" :to="`/app/cortex-checkin/${rental.name}`" class="cx-btn-primary" data-test="cta-start-checkin">
      {{ t('rental_detail.next_action_checkout') }}
    </RouterLink>
    <RouterLink v-else-if="rental.rental_state === 'Partially Returned'" :to="`/app/cortex-checkin/${rental.name}`" class="cx-btn-soft" data-test="cta-continue-checkin">
      {{ t('rental_detail.next_action_partial') }}
    </RouterLink>
    <span v-else-if="rental.rental_state === 'Invoiced'" class="cx-btn-soft" aria-disabled="true">{{ t('rental_detail.next_action_invoiced') }}</span>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { RentalTransaction } from '@/types/rental'

const { t } = useI18n()

// One primary action per view: the next legal transition for the current state (the server revalidates it).
defineProps<{ rental: RentalTransaction; isActionLoading?: boolean }>()
const emit = defineEmits<{ (e: 'action', actionName: string): void }>()
</script>
