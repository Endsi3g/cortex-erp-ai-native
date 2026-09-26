<template>
  <Dialog v-model="open" :options="{ size: 'xl', position: 'top' }">
    <template #body>
      <div role="combobox" :aria-expanded="open" aria-haspopup="listbox" :aria-owns="listId">
        <div class="relative border-b border-outline-gray-1">
          <Search class="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-ink-gray-5" :stroke-width="1.5" aria-hidden="true" />
          <input
            ref="inputRef"
            v-model="query"
            type="search"
            class="w-full border-0 bg-transparent py-3 pl-11 pr-4 text-base text-ink-gray-8 placeholder-ink-gray-4 focus:ring-0"
            :placeholder="t('search.placeholder_full')"
            :aria-label="t('search.placeholder_full')"
            :aria-controls="listId"
            :aria-activedescendant="activeItem ? `${listId}-${activeIndex}` : undefined"
            autocomplete="off"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.enter.prevent="select(activeItem)"
          />
        </div>
        <ul :id="listId" role="listbox" class="max-h-96 overflow-y-auto py-2">
          <template v-for="group in groups" :key="group.label">
            <li class="px-4 pb-1.5 pt-3 text-sm text-ink-gray-5 first:pt-1" role="presentation">{{ group.label }}</li>
            <li
              v-for="item in group.items"
              :id="`${listId}-${flat.indexOf(item)}`"
              :key="item.key"
              role="option"
              :aria-selected="item === activeItem"
              class="mx-2 flex cursor-pointer items-center gap-3 rounded px-2.5 py-2"
              :class="item === activeItem ? 'bg-surface-gray-2' : ''"
              @mouseenter="activeIndex = flat.indexOf(item)"
              @click="select(item)"
            >
              <component :is="item.icon" class="size-4 shrink-0 text-ink-gray-6" :stroke-width="1.5" aria-hidden="true" />
              <span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{ item.title }}</span>
              <span v-if="item.subtitle" class="max-w-[50%] truncate text-sm text-ink-gray-5">{{ item.subtitle }}</span>
            </li>
          </template>
          <li v-if="searching" class="px-4 py-3 text-sm text-ink-gray-5" role="status">{{ t('search.searching') }}</li>
          <li v-else-if="searchError" class="px-4 py-3 text-sm text-ink-red-4" role="status">{{ searchError }}</li>
          <li v-else-if="query.trim().length >= 2 && !flat.length" class="px-4 py-3 text-sm text-ink-gray-5" role="status">
            {{ t('search.no_results', { query: query.trim() }) }}
          </li>
        </ul>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Dialog } from 'frappe-ui'
import { Barcode, Camera, FileText, Search, Users } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'
import type { GlobalSearchResult } from '@/api/contracts'
import { useNavigationStore } from '@/stores/navigation'
import { useNavigation } from '../navigation'

interface SearchItem {
  key: string
  title: string
  subtitle?: string
  icon: Component
  to: string
}

const { t } = useI18n()
const router = useRouter()
const navigationStore = useNavigationStore()
const { items: navItems } = useNavigation()

const listId = 'cortex-search-results'
const inputRef = ref<HTMLInputElement | null>(null)
const query = ref('')
const results = ref<GlobalSearchResult[]>([])
const searching = ref(false)
const searchError = ref('')
const activeIndex = ref(0)

const open = computed({
  get: () => navigationStore.isUniversalSearchOpen,
  set: value => (value ? navigationStore.openUniversalSearch() : navigationStore.closeUniversalSearch())
})

const RESULT_META: Record<GlobalSearchResult['type'], { icon: Component; route: (id: string) => string; group: string }> = {
  rental: { icon: FileText, route: id => router.resolve({ name: 'rental-detail', params: { name: id } }).path, group: 'search.group_rentals' },
  customer: { icon: Users, route: id => router.resolve({ name: 'customer-detail', params: { customer: id } }).path, group: 'search.group_customers' },
  equipment: { icon: Camera, route: id => router.resolve({ name: 'equipment-detail', params: { item: id } }).path, group: 'search.group_equipment' },
  serial: { icon: Barcode, route: id => router.resolve({ name: 'serial-detail', params: { serial: id } }).path, group: 'search.group_serials' }
}

const groups = computed(() => {
  const needle = query.value.trim().toLowerCase()
  const screens: SearchItem[] = navItems.value
    .filter(item => !needle || item.label.toLowerCase().includes(needle))
    .map(item => ({ key: `nav:${item.name}`, title: item.label, icon: item.icon, to: item.path }))
  const out: Array<{ label: string; items: SearchItem[] }> = []
  if (screens.length) out.push({ label: t('search.group_screens'), items: needle ? screens.slice(0, 6) : screens })
  for (const type of Object.keys(RESULT_META) as GlobalSearchResult['type'][]) {
    const meta = RESULT_META[type]
    const items = results.value
      .filter(result => result.type === type)
      .map(result => ({ key: `${type}:${result.id}`, title: result.title, subtitle: result.subtitle, icon: meta.icon, to: meta.route(result.id) }))
    if (items.length) out.push({ label: t(meta.group), items })
  }
  return out
})

const flat = computed(() => groups.value.flatMap(group => group.items))
const activeItem = computed(() => flat.value[activeIndex.value])

function move(step: number) {
  if (!flat.value.length) return
  activeIndex.value = (activeIndex.value + step + flat.value.length) % flat.value.length
}

function select(item: SearchItem | undefined) {
  if (!item) return
  open.value = false
  void router.push(item.to)
}

let timer: ReturnType<typeof setTimeout> | undefined
let requestId = 0
watch(query, value => {
  activeIndex.value = 0
  searchError.value = ''
  clearTimeout(timer)
  if (value.trim().length < 2) {
    results.value = []
    searching.value = false
    return
  }
  searching.value = true
  timer = setTimeout(async () => {
    const current = ++requestId
    try {
      const response = await getCortexApiClient().globalSearch(value.trim())
      if (current === requestId) results.value = response.results
    } catch (error) {
      if (current === requestId) {
        results.value = []
        searchError.value = error instanceof Error ? error.message : t('search.failed')
      }
    } finally {
      if (current === requestId) searching.value = false
    }
  }, 250)
})

watch(open, async value => {
  if (value) {
    await nextTick()
    inputRef.value?.focus()
  } else {
    query.value = ''
    results.value = []
  }
})
</script>
