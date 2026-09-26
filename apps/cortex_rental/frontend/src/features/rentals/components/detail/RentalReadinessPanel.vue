<template>
  <section class="rounded border border-outline-gray-1" :aria-label="t('rental_detail.readiness.title')">
    <header class="flex h-10 items-center justify-between border-b border-outline-gray-1 px-4">
      <h2 class="text-base font-semibold text-ink-gray-9">{{ t('rental_detail.readiness.title') }}</h2>
      <Badge :theme="rental.readiness.overall_ready ? 'green' : 'orange'" variant="subtle">
        {{ rental.readiness.overall_ready ? t('rental_detail.readiness.ready') : t('rental_detail.readiness.incomplete') }}
      </Badge>
    </header>
    <ul class="divide-y divide-outline-gray-1">
      <li v-for="item in items" :key="item.field" class="flex min-h-[44px] items-center gap-3 px-4 py-2">
        <span
          class="flex size-5 shrink-0 items-center justify-center rounded-full"
          :class="item.done ? 'bg-surface-green-2 text-ink-green-3' : 'bg-surface-gray-2 text-ink-gray-5'"
          aria-hidden="true"
        >
          <Check v-if="item.done" class="size-3.5" :stroke-width="2" />
          <Minus v-else class="size-3.5" :stroke-width="2" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-base text-ink-gray-8">{{ item.label }}</p>
          <p class="text-sm text-ink-gray-5">{{ item.hint }}</p>
        </div>
        <Button
          v-if="item.editable && canVerify"
          size="sm"
          variant="subtle"
          :loading="saving === item.field"
          @click="toggle(item.field as ReadinessField, !item.done)"
        >
          {{ item.done ? t('rental_detail.readiness.revoke') : t('rental_detail.readiness.verify') }}
        </Button>
      </li>
    </ul>
    <p v-if="errorMessage" class="border-t border-outline-gray-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>
    <ReasonDialog
      v-model="revoking"
      :title="t('rental_detail.readiness.revoke_title')"
      :label="t('rental_detail.readiness.revoke_reason')"
      :confirm-label="t('rental_detail.readiness.revoke')"
      :cancel-label="t('common.cancel')"
      :loading="saving !== null"
      :error="errorMessage"
      danger
      @confirm="note => revokeField && save(revokeField, false, note)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge, Button, toast } from 'frappe-ui'
import { Check, Minus } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { GetRentalResponse, ReadinessField } from '@/api/contracts/rentals'
import ReasonDialog from '@/design-system/components/page/ReasonDialog.vue'

const props = defineProps<{ rental: GetRentalResponse }>()
const emit = defineEmits<{ updated: [rental: GetRentalResponse] }>()

const { t } = useI18n()
const saving = ref<string | null>(null)
const errorMessage = ref('')

const canVerify = computed(() => props.rental.available_actions.includes('verify_readiness'))

const items = computed(() => [
  { field: 'customer_account_ready', label: t('rental_detail.readiness.account'), hint: t('rental_detail.readiness.account_hint'), done: props.rental.readiness.customer_account_ready, editable: true },
  { field: 'insurance_ready', label: t('rental_detail.readiness.insurance'), hint: t('rental_detail.readiness.insurance_hint'), done: props.rental.readiness.insurance_ready, editable: true },
  { field: 'payment_ready', label: t('rental_detail.readiness.payment'), hint: t('rental_detail.readiness.payment_hint'), done: props.rental.readiness.payment_ready, editable: false }
])

const revoking = ref(false)
const revokeField = ref<ReadinessField | null>(null)

function toggle(field: ReadinessField, value: boolean) {
  if (value) return void save(field, true)
  revokeField.value = field
  errorMessage.value = ''
  revoking.value = true
}

async function save(field: ReadinessField, value: boolean, note?: string) {
  saving.value = field
  errorMessage.value = ''
  try {
    emit('updated', await getCortexApiClient().setReadiness(props.rental.id, field, value, note))
    toast.create({ message: value ? t('rental_detail.readiness.verified') : t('rental_detail.readiness.revoked'), type: 'success' })
    revoking.value = false
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    saving.value = null
  }
}
</script>
