<template>
  <div class="space-y-5" data-test="step-equipment-pricing">
    <div class="rounded-xl border border-cortex-border bg-cortex-surface p-4 space-y-3">
      <label class="block text-xs font-bold uppercase tracking-wider">Catalogue locatif ERPNext</label>
      <div class="flex gap-2"><input v-model="query" type="search" class="min-w-0 flex-1 rounded-lg border border-cortex-border px-3 py-2 text-xs" placeholder="Rechercher un équipement…" @input="searchCatalog" /><button type="button" class="cx-btn-secondary px-3 text-xs" :disabled="!selectedCode" @click="addItem">Ajouter</button></div>
      <p v-if="catalogLoading" class="text-xs text-cortex-text-muted">Recherche dans le catalogue de l’entreprise…</p>
      <div v-if="catalog.length" class="max-h-40 overflow-auto divide-y divide-cortex-border rounded-lg border border-cortex-border">
        <button v-for="item in catalog" :key="item.item_code" type="button" class="flex w-full items-center justify-between px-3 py-2 text-left text-xs hover:bg-cortex-surface-secondary" :class="selectedCode === item.item_code ? 'bg-cortex-primary-50' : ''" @click="selectedCode = item.item_code"><span>{{ item.item_name }} <span class="text-cortex-text-muted">· {{ item.item_code }}</span></span><span>{{ money(item.daily_rate) }}/jour</span></button>
      </div>
      <p v-else-if="!catalogLoading" class="text-xs text-cortex-text-muted">Aucun résultat. Le tarif affiché vient du profil locatif ERPNext.</p>
    </div>

    <div class="rounded-xl border border-cortex-border bg-cortex-surface p-4 space-y-3">
      <div class="flex justify-between text-xs font-bold uppercase"><span>Équipements sélectionnés</span><span>{{ lines.length }}</span></div>
      <div v-for="(line, index) in lines" :key="line.itemCode" class="flex flex-wrap items-center justify-between gap-3 border-t border-cortex-border py-3" :data-test="`line-item-${line.itemCode}`">
        <div><div class="text-xs font-semibold">{{ line.itemName }}</div><div class="text-[11px] text-cortex-text-muted">{{ line.itemCode }} · {{ money(line.dailyRate) }}/jour</div></div>
        <div class="flex items-center gap-2"><label class="text-[11px]">Qté <input type="number" min="1" :value="line.quantity" class="w-16 rounded border px-2 py-1" @change="setQuantity(index, Number(($event.target as HTMLInputElement).value))" /></label><button type="button" class="text-xs text-red-700" aria-label="Retirer" @click="removeLine(index)">Retirer</button></div>
      </div>
      <p v-if="!lines.length" class="py-3 text-xs text-cortex-text-muted">Ajoutez des articles réels du catalogue avant de continuer.</p>
    </div>

    <div class="rounded-xl border p-3 text-xs" :class="availability?.all_available ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50'">
      <span v-if="checking">Vérification de disponibilité auprès de Frappe…</span>
      <span v-else-if="availability">{{ availability.all_available ? 'Disponible selon les réservations actuelles' : 'Conflit détecté — vérifiez les quantités avant de continuer' }}</span>
      <span v-else>La disponibilité sera vérifiée pour les dates sélectionnées.</span>
      <div v-if="availability && !availability.all_available" class="mt-1">{{ availability.items.filter(i => !i.is_available).map(i => `${i.item_code}: ${i.available_quantity}/${i.requested_quantity} disponibles`).join(' · ') }}</div>
      <div v-if="availabilityError" class="mt-1 text-red-800">{{ availabilityError }}</div>
    </div>

    <div class="rounded-xl border border-cortex-border bg-cortex-surface-secondary p-4 text-xs space-y-2">
      <div class="flex justify-between"><span>Estimation hors taxes (tarifs ERPNext)</span><span>{{ pricing ? money(pricing.subtotal) : '—' }}</span></div>
      <div class="flex justify-between"><span>Taxes</span><span>{{ pricing ? (pricing.tax_amount ? money(pricing.tax_amount) : 'calculées lors de la création du devis ERPNext') : '—' }}</span></div>
      <div v-if="pricing" class="border-t pt-2 flex justify-between font-bold"><span>Estimation actuelle</span><span>{{ money(pricing.grand_total) }}</span></div>
      <p v-if="pricingError" class="text-amber-800">{{ pricingError }}</p>
      <p v-else class="text-[11px] text-cortex-text-muted">Montant indicatif calculé par Cortex. Les taxes officielles viennent du modèle de taxes ERPNext associé.</p>
    </div>

    <div class="flex justify-between border-t border-cortex-border pt-3"><button type="button" class="cx-btn-secondary px-3 py-2 text-xs" @click="emit('prev')">Précédent</button><button type="button" class="cx-btn-primary px-4 py-2 text-xs" :disabled="!lines.length || !pricing || checking" data-test="step2-next-btn" @click="emit('next')">Vérifier le devis</button></div>
  </div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { getCortexApiClient } from '@/api'
import type { RentalCatalogOption, PreviewPricingResponse } from '@/api/contracts/rentals'
import type { AvailabilityCheckResponse } from '@/api/contracts/availability'
export interface ComposerLineItem { itemCode: string; itemName: string; category: string; dailyRate: number; quantity: number; assignedSerials: string[] }
const props = defineProps<{ lines: ComposerLineItem[]; startsAt: string; endsAt: string }>()
const emit = defineEmits<{ (e: 'update:lines', value: ComposerLineItem[]): void; (e: 'prev'): void; (e: 'next'): void }>()
const api = getCortexApiClient(); const query = ref(''); const catalog = ref<RentalCatalogOption[]>([]); const selectedCode = ref(''); const catalogLoading = ref(false)
const pricing = ref<PreviewPricingResponse | null>(null); const pricingError = ref(''); const availability = ref<AvailabilityCheckResponse | null>(null); const availabilityError = ref(''); const checking = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | undefined; let refreshTimer: ReturnType<typeof setTimeout> | undefined; let sequence = 0
function searchCatalog() { if (searchTimer) clearTimeout(searchTimer); searchTimer = setTimeout(async () => { catalogLoading.value = true; try { catalog.value = await api.searchRentalCatalog(query.value.trim()) } catch { catalog.value = []; } finally { catalogLoading.value = false } }, 250) }
async function addItem() { const item = catalog.value.find(i => i.item_code === selectedCode.value); if (!item) return; const existing = props.lines.find(l => l.itemCode === item.item_code); const next = existing ? props.lines.map(l => l.itemCode === item.item_code ? { ...l, quantity: l.quantity + 1 } : l) : [...props.lines, { itemCode: item.item_code, itemName: item.item_name, category: item.category, dailyRate: item.daily_rate, quantity: 1, assignedSerials: [] }]; emit('update:lines', next); selectedCode.value = '' }
function setQuantity(index: number, quantity: number) { emit('update:lines', props.lines.map((l, i) => i === index ? { ...l, quantity: Math.max(1, quantity) } : l)) }
function removeLine(index: number) { emit('update:lines', props.lines.filter((_, i) => i !== index)) }
function dateTime(day: string, end = false) { return `${day}T${end ? '18:00:00' : '08:00:00'}` }
function money(value: number) { return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(value) }
watch(() => [props.lines, props.startsAt, props.endsAt] as const, () => { if (refreshTimer) clearTimeout(refreshTimer); refreshTimer = setTimeout(async () => {
  pricing.value = null; availability.value = null; pricingError.value = ''; availabilityError.value = ''
  if (!props.lines.length || !props.startsAt || !props.endsAt) return
  const current = ++sequence; checking.value = true
  try {
    const [price, stock] = await Promise.all([
      api.previewPricing({ starts_at: dateTime(props.startsAt), ends_at: dateTime(props.endsAt, true), items: props.lines.map(l => ({ item_code: l.itemCode, quantity: l.quantity })) }),
      api.checkInventoryAvailability({ starts_at: dateTime(props.startsAt), ends_at: dateTime(props.endsAt, true), items: props.lines.map(l => ({ item_code: l.itemCode, quantity: l.quantity })) })
    ])
    if (current === sequence) {
      pricing.value = price; availability.value = stock
      const repriced = props.lines.map(line => ({ ...line, dailyRate: price.lines.find(p => p.item_code === line.itemCode)?.daily_rate ?? line.dailyRate }))
      if (repriced.some((line, index) => line.dailyRate !== props.lines[index]?.dailyRate)) emit('update:lines', repriced)
    }
  } catch (error) { if (current === sequence) { pricingError.value = error instanceof Error ? error.message : 'Prix ERPNext indisponibles'; availabilityError.value = 'Vérification impossible. Ne considérez pas cet équipement comme réservé.' } }
  finally { if (current === sequence) checking.value = false }
}, 300) }, { deep: true, immediate: true })
</script>
