<template>
  <div class="space-y-5" data-test="step-equipment-pricing">
    <!-- Active 7d=3d Pricing Rule Banner -->
    <div class="p-3.5 rounded-xl border border-cortex-primary-300 bg-cortex-primary-50/50 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2" data-test="pricing-rule-banner">
      <div class="flex items-center gap-2">
        <Sparkles class="w-4 h-4 text-cortex-primary-600 flex-shrink-0" />
        <span class="font-bold text-cortex-primary-950">
          {{ t('composer.pricing_rule_badge') }}
        </span>
      </div>
      <span class="px-2 py-0.5 rounded bg-cortex-primary-200 text-cortex-primary-900 font-mono text-[11px] font-bold">
        {{ calendarDays }}j calendaires = {{ billableDays }}j facturés
      </span>
    </div>

    <!-- Catalog Item Selector -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3">
      <div class="flex items-center justify-between">
        <label class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          Ajouter un Équipement du Catalogue
        </label>
        <button
          type="button"
          class="text-xs text-cortex-primary-700 font-semibold hover:underline"
          data-test="auto-assign-serials-btn"
          @click="autoAssignSerials"
        >
          ⚡ {{ t('composer.auto_assign_serials') }}
        </button>
      </div>

      <div class="flex gap-2">
        <select
          v-model="selectedCatalogCode"
          class="flex-1 text-xs p-2.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary focus:ring-1 focus:ring-cortex-primary-500"
          data-test="catalog-select"
        >
          <option value="" disabled>Sélectionner un équipement...</option>
          <option
            v-for="item in catalog"
            :key="item.item_code"
            :value="item.item_code"
          >
            {{ item.item_name }} ({{ formatCurrency(item.daily_rate) }}/j) — Dispo: {{ item.available_quantity }}
          </option>
        </select>

        <button
          type="button"
          class="cx-btn-secondary text-xs px-3.5 py-2 flex items-center gap-1.5"
          :disabled="!selectedCatalogCode"
          data-test="add-equipment-btn"
          @click="addItem"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>Ajouter</span>
        </button>
      </div>
    </div>

    <!-- Selected Line Items Table -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-3">
      <div class="flex items-center justify-between border-b border-cortex-border pb-2.5">
        <h3 class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          Équipements Sélectionnés ({{ lines.length }})
        </h3>
        <!-- Availability Check Status Chip -->
        <div class="flex items-center gap-1.5">
          <span
            v-if="isCheckingAvailability"
            class="text-[11px] text-cortex-text-muted flex items-center gap-1 font-medium"
          >
            <RefreshCw class="w-3 h-3 animate-spin" />
            Contrôle disponibilité...
          </span>
          <span
            v-else-if="allAvailable"
            class="px-2 py-0.5 rounded-full bg-cortex-primary-100 text-cortex-primary-800 text-[10px] font-bold"
            data-test="availability-chip-success"
          >
            ✓ Stock Disponible
          </span>
          <span
            v-else
            class="px-2 py-0.5 rounded-full bg-red-100 text-red-800 text-[10px] font-bold"
            data-test="availability-chip-conflict"
          >
            ⚠ Stock Insuffisant
          </span>
        </div>
      </div>

      <div class="divide-y divide-cortex-border">
        <div
          v-for="(line, index) in lines"
          :key="line.itemCode"
          class="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          :data-test="`line-item-${line.itemCode}`"
        >
          <div class="min-w-0">
            <span class="text-xs font-semibold text-cortex-text-primary block truncate">
              {{ line.itemName }}
            </span>
            <div class="flex flex-wrap items-center gap-2 mt-0.5">
              <span class="text-[10px] font-mono text-cortex-primary-700 bg-cortex-primary-50 px-1 rounded">
                {{ line.itemCode }}
              </span>
              <span class="text-[11px] text-cortex-text-muted">
                {{ formatCurrency(line.dailyRate) }} / jour × {{ billableDays }} jours facturés
              </span>
            </div>

            <!-- Assigned Serials Chips -->
            <div v-if="line.assignedSerials.length > 0" class="mt-1.5 flex flex-wrap items-center gap-1">
              <span class="text-[10px] text-cortex-text-muted">Séries :</span>
              <span
                v-for="sn in line.assignedSerials"
                :key="sn"
                class="px-1.5 py-0.2 rounded bg-cortex-surface-secondary text-[10px] font-mono text-cortex-text-primary border border-cortex-border"
              >
                {{ sn }}
              </span>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <div class="flex items-center gap-1.5">
              <label class="text-[11px] text-cortex-text-muted">Qté :</label>
              <input
                type="number"
                min="1"
                :value="line.quantity"
                class="w-14 text-xs p-1 rounded border border-cortex-border text-center font-mono"
                @input="updateLineQuantity(index, Number(($event.target as HTMLInputElement).value))"
              />
            </div>

            <span class="font-mono font-bold text-xs text-cortex-text-primary min-w-[80px] text-right">
              {{ formatCurrency(line.dailyRate * line.quantity * billableDays) }}
            </span>

            <button
              type="button"
              class="p-1 rounded text-cortex-text-muted hover:text-red-600 hover:bg-red-50"
              title="Supprimer"
              @click="removeLine(index)"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div v-if="lines.length === 0" class="py-6 text-center text-xs text-cortex-text-muted">
          Aucun équipement ajouté pour le moment.
        </div>
      </div>
    </div>

    <!-- Accessory Suggestions Banner -->
    <div
      v-if="suggestedAccessories.length > 0"
      class="p-3.5 rounded-xl border border-cortex-border bg-cortex-surface shadow-2xs space-y-2"
      data-test="accessories-suggestion-banner"
    >
      <div class="flex items-center gap-1.5 text-xs font-bold text-cortex-text-primary">
        <PackageCheck class="w-4 h-4 text-cortex-primary-600" />
        <span>{{ t('composer.accessories_banner') }}</span>
      </div>
      <div class="flex flex-wrap gap-1.5 pt-1">
        <span
          v-for="acc in suggestedAccessories"
          :key="acc.name"
          class="px-2 py-0.5 rounded-full text-[11px] font-medium border"
          :class="acc.required ? 'bg-amber-50 border-amber-300 text-amber-900 font-semibold' : 'bg-cortex-surface-secondary border-cortex-border text-cortex-text-secondary'"
        >
          {{ acc.required ? '[Requis]' : '[Optionnel]' }} {{ acc.name }}
        </span>
      </div>
    </div>

    <!-- Financial Breakdown Card -->
    <div class="p-4 rounded-xl border border-cortex-border bg-cortex-surface-secondary space-y-2 text-xs">
      <div class="flex items-center justify-between text-cortex-text-secondary">
        <span>Sous-total HT ({{ billableDays }} jours facturés sur {{ calendarDays }} calendaires) :</span>
        <span class="font-mono font-semibold">{{ formatCurrency(subtotal) }}</span>
      </div>
      <div class="flex items-center justify-between text-cortex-text-secondary">
        <span>Taxes applicables (TPS 5% + TVQ 9.975% = 14.975%) :</span>
        <span class="font-mono font-semibold">{{ formatCurrency(taxAmount) }}</span>
      </div>
      <div class="flex items-center justify-between text-sm font-bold text-cortex-text-primary pt-2 border-t border-cortex-border">
        <span>Total TTC (CAD) :</span>
        <span class="font-mono text-base text-cortex-primary-800" data-test="composer-grand-total">
          {{ formatCurrency(grandTotal) }}
        </span>
      </div>
    </div>

    <!-- Step Navigation Buttons -->
    <div class="pt-3 border-t border-cortex-border flex items-center justify-between">
      <button
        type="button"
        class="cx-btn-secondary text-xs px-3.5 py-2 flex items-center gap-1.5"
        @click="emit('prev')"
      >
        <ArrowLeft class="w-3.5 h-3.5" />
        <span>Précédent : Client & Dates</span>
      </button>

      <button
        type="button"
        class="cx-btn-primary text-xs px-4 py-2 flex items-center gap-1.5"
        :disabled="lines.length === 0"
        data-test="step2-next-btn"
        @click="emit('next')"
      >
        <span>Suivant : Vérifier & Créer</span>
        <ArrowRight class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sparkles, Plus, Trash2, ArrowRight, ArrowLeft, RefreshCw, PackageCheck } from 'lucide-vue-next'
import { initialCatalog } from '@/api/mock/fixtures/catalog'
import { initialSerials } from '@/api/mock/fixtures/serials'
import { calculateBillableDays } from '@/api/mock/MockCortexApiClient'
import { getCortexApiClient } from '@/api'

const { t } = useI18n()

export interface ComposerLineItem {
  itemCode: string
  itemName: string
  category: string
  dailyRate: number
  quantity: number
  assignedSerials: string[]
}

const props = defineProps<{
  lines: ComposerLineItem[]
  startsAt: string
  endsAt: string
}>()

const emit = defineEmits<{
  (e: 'update:lines', val: ComposerLineItem[]): void
  (e: 'prev'): void
  (e: 'next'): void
}>()

const catalog = initialCatalog
const selectedCatalogCode = ref<string>('')
const isCheckingAvailability = ref<boolean>(false)
const allAvailable = ref<boolean>(true)

const calendarDays = computed(() => {
  if (!props.startsAt || !props.endsAt) return 7
  const start = new Date(props.startsAt)
  const end = new Date(props.endsAt)
  const diffTime = Math.abs(end.getTime() - start.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return diffDays > 0 ? diffDays : 1
})

const billableDays = computed(() => {
  return calculateBillableDays(calendarDays.value)
})

const subtotal = computed(() => {
  return props.lines.reduce((acc, line) => {
    return acc + line.dailyRate * line.quantity * billableDays.value
  }, 0)
})

const taxAmount = computed(() => {
  return Math.round(subtotal.value * 0.14975 * 100) / 100
})

const grandTotal = computed(() => {
  return subtotal.value + taxAmount.value
})

const suggestedAccessories = computed(() => {
  const accList: Array<{ name: string; required: boolean }> = []
  for (const line of props.lines) {
    const catItem = catalog.find(c => c.item_code === line.itemCode)
    if (catItem) {
      if (catItem.required_accessories) {
        catItem.required_accessories.forEach(acc => accList.push({ name: acc, required: true }))
      }
      if (catItem.optional_accessories) {
        catItem.optional_accessories.forEach(acc => accList.push({ name: acc, required: false }))
      }
    }
  }
  return accList
})

const addItem = () => {
  if (!selectedCatalogCode.value) return
  const item = catalog.find(c => c.item_code === selectedCatalogCode.value)
  if (!item) return

  const existingIndex = props.lines.findIndex(l => l.itemCode === item.item_code)
  if (existingIndex >= 0) {
    const updated = [...props.lines]
    const cur = updated[existingIndex]
    if (cur) {
      cur.quantity += 1
    }
    emit('update:lines', updated)
  } else {
    emit('update:lines', [
      ...props.lines,
      {
        itemCode: item.item_code,
        itemName: item.item_name,
        category: item.category,
        dailyRate: item.daily_rate,
        quantity: 1,
        assignedSerials: []
      }
    ])
  }
  selectedCatalogCode.value = ''
}

const updateLineQuantity = (index: number, quantity: number) => {
  const updated = [...props.lines]
  const cur = updated[index]
  if (cur) {
    cur.quantity = Math.max(1, quantity)
  }
  emit('update:lines', updated)
}

const removeLine = (index: number) => {
  const updated = props.lines.filter((_, i) => i !== index)
  emit('update:lines', updated)
}

const autoAssignSerials = () => {
  const updated = props.lines.map(line => {
    const available = initialSerials
      .filter(s => s.item_code === line.itemCode && s.status === 'Available')
      .slice(0, line.quantity)
      .map(s => s.serial_number)
    return {
      ...line,
      assignedSerials: available
    }
  })
  emit('update:lines', updated)
}

// Debounce 400ms availability check
let availTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => props.lines,
  () => {
    if (props.lines.length === 0) {
      allAvailable.value = true
      return
    }
    if (availTimer) clearTimeout(availTimer)
    isCheckingAvailability.value = true
    availTimer = setTimeout(async () => {
      try {
        const client = getCortexApiClient()
        const res = await client.checkInventoryAvailability({
          items: props.lines.map(l => ({ item_code: l.itemCode, quantity: l.quantity })),
          starts_at: props.startsAt || '2026-09-10T08:00:00Z',
          ends_at: props.endsAt || '2026-09-17T18:00:00Z'
        })
        allAvailable.value = res.all_available
      } catch {
        allAvailable.value = true
      } finally {
        isCheckingAvailability.value = false
      }
    }, 400)
  },
  { deep: true }
)

const formatCurrency = (amt: number) => {
  return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(amt)
}
</script>
