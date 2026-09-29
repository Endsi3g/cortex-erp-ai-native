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
            <p v-if="searching" class="flex items-center gap-2 px-2.5 text-[11px] text-cortex-text-muted" role="status"><Loader2 class="w-3.5 h-3.5 animate-spin" /> Recherche dans Cortex…</p>
            <p v-else-if="searchFailed" class="px-2.5 text-[11px] text-red-700" role="alert">La recherche sur le serveur est indisponible. Les pages restent accessibles.</p>

            <div
              v-if="filteredGroups.length === 0 && !searching"
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
            <span class="text-[10px] text-cortex-text-muted">Pages, locations et équipement</span>
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

import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Search, X, FileSpreadsheet, Package, PlusCircle, FileQuestion, Compass, Loader2 } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import { routes } from '@/app/router/routes'
import { useNavigationStore } from '@/stores/navigation'
import { useSessionStore } from '@/stores/session'

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
const session = useSessionStore()

const query = ref('')
const searchInputRef = ref<HTMLInputElement | null>(null)
const selectedId = ref<string>('')
const remote = ref<SearchGroup[]>([])
const searching = ref(false)
const searchFailed = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null
let requestId = 0

// Navigation targets come from the route table (permission-filtered): no record is ever invented here.
const pages = computed<SearchItem[]>(() =>
  routes
    .filter((route) => route.meta && route.meta.requiresAuth && !route.meta.hideInSidebar && !route.path.includes(':') && typeof route.meta.titleKey === 'string')
    .filter((route) => !route.meta?.requiredPermission || session.hasPermission(route.meta.requiredPermission as string))
    .map((route) => ({ id: `page:${String(route.name)}`, label: t(route.meta!.titleKey as string), to: route.path, icon: Compass, badge: 'Page' }))
)

const quickActions = computed<SearchItem[]>(() =>
  session.hasPermission('cortex:quote:create')
    ? [{ id: 'act:new-rental', label: t('routes.rental_composer'), sublabel: 'Créer un devis ou une réservation', to: '/app/cortex-rental/new', icon: PlusCircle, badge: 'Action' }]
    : []
)

const normalized = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

const filteredGroups = computed<SearchGroup[]>(() => {
  const q = normalized(query.value.trim())
  const match = (item: SearchItem) => !q || normalized(item.label).includes(q) || normalized(item.sublabel || '').includes(q)
  const local: SearchGroup[] = [
    { title: 'Actions rapides', items: quickActions.value.filter(match) },
    { title: 'Aller à', items: pages.value.filter(match) }
  ]
  return [...remote.value, ...local].filter((group) => group.items.length > 0)
})

const allFilteredItems = computed<SearchItem[]>(() => filteredGroups.value.flatMap((g) => g.items))

async function searchServer(text: string) {
  const current = ++requestId
  searching.value = true
  searchFailed.value = false
  try {
    const client = getCortexApiClient()
    const [rentals, equipment] = await Promise.all([
      session.hasPermission('cortex:rental:view') ? client.listRentals({ search: text, page: 1, page_size: 5 }) : Promise.resolve(null),
      session.hasPermission('cortex:catalog:view') ? client.listEquipment({ search: text, page: 1, page_size: 5 }) : Promise.resolve(null)
    ])
    if (current !== requestId) return
    const groups: SearchGroup[] = []
    if (rentals?.items.length) {
      groups.push({
        title: 'Locations',
        items: rentals.items.map((rental) => ({ id: `rental:${rental.name}`, label: rental.project_name || rental.customer_name, sublabel: `${rental.name} · ${rental.customer_name}`, to: `/app/cortex-rental/${rental.name}`, icon: FileSpreadsheet, badge: rental.rental_state }))
      })
    }
    if (equipment?.items.length) {
      groups.push({
        title: 'Équipement',
        items: equipment.items.map((item) => ({ id: `item:${item.item_code}`, label: item.item_name, sublabel: item.item_code, to: `/app/cortex-equipment/${item.item_code}`, icon: Package, badge: item.category }))
      })
    }
    remote.value = groups
  } catch {
    if (current === requestId) {
      remote.value = []
      searchFailed.value = true
    }
  } finally {
    if (current === requestId) searching.value = false
  }
}

watch(query, (value) => {
  if (timer) clearTimeout(timer)
  const text = value.trim()
  if (text.length < 2) {
    requestId++
    remote.value = []
    searching.value = false
    searchFailed.value = false
    return
  }
  timer = setTimeout(() => searchServer(text), 250)
})

watch(allFilteredItems, (items) => {
  if (!items.some((item) => item.id === selectedId.value)) selectedId.value = items[0]?.id ?? ''
}, { immediate: true })

const navigateTo = (path: string) => {
  navigationStore.closeUniversalSearch()
  router.push(path)
}

const navigateResults = (direction: number) => {
  const items = allFilteredItems.value
  if (items.length === 0) return
  const currentIndex = items.findIndex((i) => i.id === selectedId.value)
  let newIndex = currentIndex + direction
  if (newIndex < 0) newIndex = items.length - 1
  if (newIndex >= items.length) newIndex = 0
  selectedId.value = items[newIndex].id
}

const selectActiveResult = () => {
  const item = allFilteredItems.value.find((i) => i.id === selectedId.value)
  if (item) navigateTo(item.to)
}

watch(
  () => navigationStore.isUniversalSearchOpen,
  (open) => {
    if (open) {
      query.value = ''
      remote.value = []
      nextTick(() => searchInputRef.value?.focus())
    }
  }
)

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>
