<template>
  <div>
    <!-- Search Trigger Button in Topbar -->
    <button
      v-if="!modalOnly"
      type="button"
      @click="navigationStore.openUniversalSearch"
      class="flex items-center justify-between w-full max-w-[240px] md:max-w-[280px] px-3 py-1.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-muted text-xs font-normal hover:border-cortex-primary-400 hover:text-cortex-text-primary transition-all shadow-xs group focus:outline-none focus:ring-2 focus:ring-cortex-primary-500"
      :aria-label="t('common.search_placeholder')"
    >
      <div class="flex items-center gap-2 truncate">
        <Search class="w-3.5 h-3.5 text-cortex-text-muted group-hover:text-cortex-primary-600 transition-colors flex-shrink-0" />
        <span class="truncate">{{ t('common.search_placeholder').split('(')[0].trim() }}</span>
      </div>
      <kbd class="hidden sm:inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-mono rounded bg-cortex-surface-subtle border border-cortex-border text-cortex-text-muted flex-shrink-0">
        ⌘K
      </kbd>
    </button>

    <!-- Modal Backdrop & Dialog -->
    <Teleport to="body">
      <div
        v-if="navigationStore.isUniversalSearchOpen"
        class="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-cortex-ink-900/60 backdrop-blur-xs animate-in fade-in duration-150"
        @click.self="navigationStore.closeUniversalSearch"
        role="dialog"
        aria-modal="true"
        aria-labelledby="universal-search-title"
      >
        <div class="w-full max-w-2xl rounded-2xl border border-cortex-border bg-cortex-surface shadow-2xl overflow-hidden flex flex-col max-h-[80vh] animate-in zoom-in-95 duration-150">
          <!-- Search Header Input -->
          <div class="flex items-center gap-3 px-4 py-3.5 border-b border-cortex-border bg-cortex-surface">
            <Search class="w-5 h-5 text-cortex-primary-600 flex-shrink-0" />
            <input
              ref="searchInputRef"
              v-model="query"
              type="text"
              class="w-full bg-transparent text-sm text-cortex-text-primary placeholder:text-cortex-text-muted focus:outline-none font-sans"
              :placeholder="t('search.placeholder')"
              @keydown.down.prevent="navigateResults(1)"
              @keydown.up.prevent="navigateResults(-1)"
              @keydown.enter.prevent="selectActiveResult"
              @keydown.esc.prevent="navigationStore.closeUniversalSearch"
            />
            <button
              type="button"
              @click="navigationStore.closeUniversalSearch"
              class="p-1 rounded-md text-cortex-text-muted hover:text-cortex-text-primary hover:bg-cortex-surface-subtle focus:outline-none"
              aria-label="Fermer"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- Results List Area -->
          <div class="flex-1 overflow-y-auto p-3 space-y-4">
            <!-- Filtered Search Results -->
            <div
              v-for="group in filteredGroups"
              :key="group.title"
              class="space-y-1"
            >
              <div class="px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-cortex-text-muted">
                {{ group.title }}
              </div>

              <button
                v-for="item in group.items"
                :key="item.id"
                type="button"
                @click="navigateTo(item.to)"
                class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-left text-xs transition-colors group/item"
                :class="[
                  selectedId === item.id
                    ? 'bg-cortex-primary-50 text-cortex-primary-900 font-semibold'
                    : 'text-cortex-text-primary hover:bg-cortex-surface-subtle'
                ]"
              >
                <div class="flex items-center gap-2.5 truncate">
                  <component
                    :is="item.icon"
                    class="w-4 h-4 flex-shrink-0 text-cortex-text-muted group-hover/item:text-cortex-primary-600"
                  />
                  <div class="flex flex-col truncate">
                    <span class="truncate">{{ item.label }}</span>
                    <span v-if="item.sublabel" class="text-[10px] text-cortex-text-muted font-mono">
                      {{ item.sublabel }}
                    </span>
                  </div>
                </div>

                <span class="text-[10px] font-mono text-cortex-text-muted group-hover/item:text-cortex-primary-700 flex-shrink-0">
                  {{ item.badge || 'Entrée' }}
                </span>
              </button>
            </div>

            <!-- Empty State -->
            <div
              v-if="filteredGroups.length === 0"
              class="py-12 text-center text-xs text-cortex-text-muted flex flex-col items-center gap-2"
            >
              <FileQuestion class="w-8 h-8 text-cortex-ink-200" />
              <span>{{ t('search.no_results') }}</span>
            </div>
          </div>

          <!-- Footer Shortcut Bar -->
          <div class="flex items-center justify-between px-4 py-2.5 border-t border-cortex-border bg-cortex-surface-subtle text-[11px] text-cortex-text-muted">
            <div class="flex items-center gap-3">
              <span class="inline-flex items-center gap-1">
                <kbd class="px-1 py-0.5 rounded bg-cortex-surface border border-cortex-border text-[10px]">↑</kbd>
                <kbd class="px-1 py-0.5 rounded bg-cortex-surface border border-cortex-border text-[10px]">↓</kbd>
                Naviguer
              </span>
              <span class="inline-flex items-center gap-1">
                <kbd class="px-1.5 py-0.5 rounded bg-cortex-surface border border-cortex-border text-[10px]">↵</kbd>
                Sélectionner
              </span>
              <span class="inline-flex items-center gap-1">
                <kbd class="px-1 py-0.5 rounded bg-cortex-surface border border-cortex-border text-[10px]">Échap</kbd>
                Fermer
              </span>
            </div>
            <span class="font-mono text-[10px] text-cortex-primary-700 font-medium">Cortex Server Search</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  modalOnly?: boolean
}>(), {
  modalOnly: false
})

import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  Search,
  X,
  FileSpreadsheet,
  Package,
  Barcode,
  ShieldCheck,
  PlusCircle,
  LogOut,
  LogIn,
  CalendarRange,
  FileQuestion
} from 'lucide-vue-next'
import { useNavigationStore } from '@/stores/navigation'

interface SearchItem {
  id: string
  label: string
  sublabel?: string
  to: string
  icon: unknown
  badge?: string
}

interface SearchGroup {
  title: string
  items: SearchItem[]
}

const { t } = useI18n()
const router = useRouter()
const navigationStore = useNavigationStore()

const query = ref('')
const searchInputRef = ref<HTMLInputElement | null>(null)
const selectedId = ref<string>('act-1')

const rawGroups: SearchGroup[] = [
  {
    title: 'Actions Rapides',
    items: [
      { id: 'act-1', label: 'Nouvelle Location (Composer)', sublabel: 'Créer devis ou réservation', to: '/app/cortex-rental/new', icon: PlusCircle, badge: 'P0' },
      { id: 'act-2', label: 'Scanner Sorties (Check-out)', sublabel: 'Validation matériel sortant', to: '/app/cortex-checkout/DEMO-TRX-2026-006', icon: LogOut, badge: 'Scanner' },
      { id: 'act-3', label: 'Scanner Retours (Check-in)', sublabel: 'Vérification retours & anomalies', to: '/app/cortex-checkin/DEMO-TRX-2026-001', icon: LogIn, badge: 'Scanner' },
      { id: 'act-4', label: 'Matrice de Disponibilité', sublabel: 'Vue grille temporelle', to: '/app/cortex-availability', icon: CalendarRange, badge: 'P0' }
    ]
  },
  {
    title: 'Locations & Transactions',
    items: [
      { id: 'trx-1', label: 'Production Nord Inc.', sublabel: 'DEMO-TRX-2026-001 · Checked Out · 4 500,00 $', to: '/app/cortex-rental/DEMO-TRX-2026-001', icon: FileSpreadsheet, badge: 'Checked Out' },
      { id: 'trx-2', label: 'Studio Lumière Montréal', sublabel: 'DEMO-TRX-2026-002 · Reservation · 7j=3j', to: '/app/cortex-rental/DEMO-TRX-2026-002', icon: FileSpreadsheet, badge: 'Reservation' },
      { id: 'trx-3', label: 'Trequista Events', sublabel: 'DEMO-TRX-2026-003 · Quote Draft', to: '/app/cortex-rental/DEMO-TRX-2026-003', icon: FileSpreadsheet, badge: 'Quote' }
    ]
  },
  {
    title: 'Catalogue & Séries',
    items: [
      { id: 'itm-1', label: 'ARRI Alexa 35 Camera Package', sublabel: 'DEMO-ITM-ALX35 · 4 unités disponibles', to: '/app/cortex-equipment/DEMO-ITM-ALX35', icon: Package, badge: 'ARRI' },
      { id: 'itm-2', label: 'RED V-Raptor XL 8K Production Pack', sublabel: 'DEMO-ITM-VRP8K · 2 unités', to: '/app/cortex-equipment/DEMO-ITM-VRP8K', icon: Package, badge: 'RED' },
      { id: 'sn-1', label: 'SN: DEMO-SN-ALX-001 (ARRI Alexa 35)', sublabel: 'Statut: Sorti · Propriétaire: Minerva', to: '/app/cortex-serial/DEMO-SN-ALX-001', icon: Barcode, badge: 'Série' }
    ]
  },
  {
    title: 'File d\'Approbation',
    items: [
      { id: 'apr-1', label: 'Approbation Contrat · Trequista Events', sublabel: 'DEMO-APR-001 · Assurance requise', to: '/app/cortex-approvals', icon: ShieldCheck, badge: 'Urgent' },
      { id: 'apr-2', label: 'Remise Dérogatoire 25% · Cooke S4/i', sublabel: 'DEMO-APR-002 · Seuil dépassé', to: '/app/cortex-approvals', icon: ShieldCheck, badge: 'Tarif' }
    ]
  }
]

const filteredGroups = computed(() => {
  if (!query.value.trim()) {
    return rawGroups
  }
  const q = query.value.toLowerCase()
  return rawGroups
    .map(group => ({
      title: group.title,
      items: group.items.filter(
        item =>
          item.label.toLowerCase().includes(q) ||
          (item.sublabel && item.sublabel.toLowerCase().includes(q)) ||
          item.id.toLowerCase().includes(q)
      )
    }))
    .filter(group => group.items.length > 0)
})

const allFilteredItems = computed<SearchItem[]>(() => {
  return filteredGroups.value.flatMap(g => g.items)
})

const navigateTo = (path: string) => {
  navigationStore.closeUniversalSearch()
  router.push(path)
}

const navigateResults = (direction: number) => {
  const items = allFilteredItems.value
  if (items.length === 0) return

  const currentIndex = items.findIndex(i => i.id === selectedId.value)
  let newIndex = currentIndex + direction
  if (newIndex < 0) newIndex = items.length - 1
  if (newIndex >= items.length) newIndex = 0

  selectedId.value = items[newIndex].id
}

const selectActiveResult = () => {
  const item = allFilteredItems.value.find(i => i.id === selectedId.value)
  if (item) {
    navigateTo(item.to)
  }
}

watch(
  () => navigationStore.isUniversalSearchOpen,
  (open) => {
    if (open) {
      query.value = ''
      selectedId.value = 'act-1'
      nextTick(() => {
        searchInputRef.value?.focus()
      })
    }
  }
)
</script>
