<template>
  <div class="space-y-5" data-test="step-review-create">
    <section class="rounded-xl border border-cortex-border bg-white p-4 space-y-3">
      <div class="flex items-center justify-between"><h2 class="text-sm font-bold">Vérification du devis</h2><span class="rounded bg-cortex-primary-50 px-2 py-1 text-[11px]">Calcul serveur</span></div>
      <p class="text-xs">Client ERPNext : <strong>{{ step1.customerName }}</strong> · Assurance : vérification nécessaire selon le dossier client.</p>
      <p class="text-xs">Période : {{ step1.startsAt }} → {{ step1.endsAt }} · {{ step1.projectName || 'Projet sans nom' }}</p>
      <div class="divide-y divide-cortex-border border-y"> <div v-for="line in lines" :key="line.itemCode" class="flex justify-between py-2 text-xs"><span>{{ line.quantity }} × {{ line.itemName }} ({{ line.itemCode }})</span><span>{{ money(line.dailyRate) }}/jour</span></div></div>
      <div v-if="loading" class="text-xs text-cortex-text-muted">Recalcul des tarifs et règles locatives…</div>
      <div v-else-if="pricing" class="space-y-2 text-xs"><div class="flex justify-between"><span>Sous-total</span><strong>{{ money(pricing.subtotal) }}</strong></div><div class="flex justify-between"><span>Taxes ERPNext</span><span>{{ pricing.tax_amount ? money(pricing.tax_amount) : 'À calculer via le modèle de taxes ERPNext' }}</span></div><div class="flex justify-between border-t pt-2 text-sm font-bold"><span>Estimation</span><span>{{ money(pricing.grand_total) }}</span></div><p class="text-[11px] text-cortex-text-muted">Règle appliquée : {{ pricing.pricing_rule_applied }}. Le devis ERPNext reste la référence fiscale.</p></div>
      <p v-if="errorMessage" class="rounded border border-red-200 bg-red-50 p-3 text-xs text-red-800">{{ errorMessage }}</p>
    </section>
    <div class="flex flex-wrap justify-between gap-2 border-t pt-3"><button type="button" class="cx-btn-secondary px-3 py-2 text-xs" :disabled="isSubmitting" @click="emit('prev')">Précédent</button><div class="flex gap-2"><button type="button" class="cx-btn-secondary px-4 py-2 text-xs" :disabled="!pricing || isSubmitting" data-test="create-quote-action-btn" @click="create('Quote')">{{ isSubmitting && action === 'Quote' ? 'Enregistrement…' : 'Créer un devis' }}</button><button type="button" class="cx-btn-primary px-4 py-2 text-xs" :disabled="!pricing || isSubmitting || !available" data-test="confirm-reservation-action-btn" @click="create('Reservation')">{{ isSubmitting && action === 'Reservation' ? 'Enregistrement…' : 'Demander la réservation' }}</button></div></div>
    <p v-if="availability && !available" class="text-xs text-amber-800">Un conflit bloque la réservation. Créez un devis ou revenez modifier les équipements.</p>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getCortexApiClient } from '@/api'
import type { PreviewPricingResponse } from '@/api/contracts/rentals'
import type { AvailabilityCheckResponse } from '@/api/contracts/availability'
import type { ComposerStep1Data } from './StepClientDates.vue'
import type { ComposerLineItem } from './StepEquipmentPricing.vue'
const props = defineProps<{ step1: ComposerStep1Data; lines: ComposerLineItem[] }>()
const emit = defineEmits<{ (e: 'prev'): void }>()
const api = getCortexApiClient(); const router = useRouter(); const pricing = ref<PreviewPricingResponse | null>(null); const availability = ref<AvailabilityCheckResponse | null>(null); const loading = ref(false); const isSubmitting = ref(false); const errorMessage = ref(''); const action = ref<'Quote' | 'Reservation'>('Quote')
const available = computed(() => availability.value?.all_available === true)
function money(value: number) { return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(value) }
watch(() => [props.step1, props.lines] as const, async () => {
  pricing.value = null; availability.value = null; errorMessage.value = ''
  if (!props.step1.customerId || !props.step1.startsAt || !props.step1.endsAt || !props.lines.length) return
  loading.value = true
  const input = { starts_at: `${props.step1.startsAt}T08:00:00`, ends_at: `${props.step1.endsAt}T18:00:00`, items: props.lines.map(line => ({ item_code: line.itemCode, quantity: line.quantity })) }
  try { [pricing.value, availability.value] = await Promise.all([api.previewPricing({ ...input, customer_id: props.step1.customerId }), api.checkInventoryAvailability(input)]) }
  catch (error) { errorMessage.value = error instanceof Error ? error.message : 'Le serveur n’a pas pu vérifier les tarifs.' }
  finally { loading.value = false }
}, { immediate: true, deep: true })
async function create(kind: 'Quote' | 'Reservation') {
  if (isSubmitting.value || !pricing.value) return
  action.value = kind; isSubmitting.value = true; errorMessage.value = ''
  try {
    const draft = await api.createQuoteDraft({ customer_id: props.step1.customerId, starts_at: `${props.step1.startsAt}T08:00:00`, ends_at: `${props.step1.endsAt}T18:00:00`, project_name: props.step1.projectName || undefined, notes: props.step1.notes || undefined, items: props.lines.map(line => ({ item_code: line.itemCode, quantity: line.quantity })) })
    if (!draft.entity_id || draft.status !== 'completed') throw new Error(draft.errors?.[0]?.message || 'Le serveur n’a pas confirmé la création du devis.')
    let targetId = draft.entity_id
    if (kind === 'Reservation') {
      const result = await api.requestReservation({ rental_id: targetId, version: 1 })
      if (result.status !== 'completed' || !result.mutation_performed) throw new Error(result.errors?.[0]?.message || 'La réservation n’a pas été confirmée; le devis reste enregistré.')
    }
    await router.push(`/app/cortex-rental/${targetId}`)
  } catch (error) { errorMessage.value = error instanceof Error ? error.message : 'Erreur inattendue lors de l’enregistrement.' }
  finally { isSubmitting.value = false }
}
</script>
