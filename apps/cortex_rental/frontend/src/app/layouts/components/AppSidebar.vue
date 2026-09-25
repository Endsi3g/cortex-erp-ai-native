<template>
  <!--
    Navigation rail — ERPNext reference (inspiration/image.png): 49px + 1px
    border, #F8F8F8, 22px mark centred in the 48px top band, 16px icons on a
    34px pitch starting 69px from the top. Expanded (220px) is opt-in and
    remembered per browser.
  -->
  <nav
    class="flex h-full shrink-0 select-none flex-col border-r border-outline-gray-2 bg-surface-menu-bar transition-[width] duration-150 ease-out"
    :class="expanded ? 'w-55' : 'w-12.5'"
    :aria-label="t('common.navigation.main')"
  >
    <div class="flex h-12 shrink-0 items-center" :class="expanded ? 'px-[13px]' : 'justify-center'">
      <RouterLink
        :to="{ name: 'operations-overview' }"
        class="flex items-center gap-2 rounded outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        :aria-label="t('common.navigation.home')"
        @click="$emit('navigate')"
      >
        <CortexMark class="size-[22px] shrink-0" />
        <span v-if="expanded" class="text-base font-semibold text-ink-gray-9">Cortex</span>
      </RouterLink>
    </div>

    <div class="flex flex-1 flex-col overflow-y-auto overflow-x-hidden px-[10px] pb-3 pt-[15px]">
      <div
        v-for="group in groups"
        :key="group.category"
        class="flex flex-col gap-1.5 [&:not(:first-child)]:mt-1.5"
        role="group"
        :aria-label="group.label"
      >
        <p v-if="expanded" class="mt-2 px-[5px] text-sm text-ink-gray-5 first:mt-0">{{ group.label }}</p>
        <Tooltip
          v-for="item in group.items"
          :key="item.name"
          :text="item.label"
          placement="right"
          :hover-delay="0.3"
          :disabled="expanded"
        >
          <RouterLink
            :to="item.path"
            class="flex h-7 shrink-0 items-center gap-2 rounded px-[6px] text-base text-ink-gray-8 outline-none transition-colors hover:bg-surface-gray-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
            :class="[
              expanded ? 'w-full' : 'w-7',
              isActive(item) ? 'bg-surface-selected text-ink-gray-9 shadow-sm hover:bg-surface-selected' : ''
            ]"
            :aria-label="item.label"
            :aria-current="isActive(item) ? 'page' : undefined"
            @click="$emit('navigate')"
          >
            <component :is="item.icon" class="size-4 shrink-0" :stroke-width="1.5" aria-hidden="true" />
            <span v-if="expanded" class="truncate">{{ item.label }}</span>
          </RouterLink>
        </Tooltip>
      </div>
    </div>

    <div v-if="collapsible" class="shrink-0 px-[10px] pb-3">
      <Tooltip :text="expanded ? t('common.actions.collapse_sidebar') : t('common.actions.expand_sidebar')" placement="right" :disabled="expanded">
        <button
          type="button"
          class="flex h-7 items-center gap-2 rounded px-[6px] text-base text-ink-gray-6 outline-none hover:bg-surface-gray-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          :class="expanded ? 'w-full' : 'w-7'"
          :aria-label="expanded ? t('common.actions.collapse_sidebar') : t('common.actions.expand_sidebar')"
          :aria-expanded="expanded"
          @click="navigationStore.toggleSidebar"
        >
          <PanelLeftClose v-if="expanded" class="size-4 shrink-0" :stroke-width="1.5" aria-hidden="true" />
          <PanelLeftOpen v-else class="size-4 shrink-0" :stroke-width="1.5" aria-hidden="true" />
          <span v-if="expanded">{{ t('common.actions.collapse_sidebar') }}</span>
        </button>
      </Tooltip>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Tooltip } from 'frappe-ui'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'
import { useNavigationStore } from '@/stores/navigation'
import { useNavigation, type NavItem } from '../navigation'
import CortexMark from './CortexMark.vue'

const props = withDefaults(defineProps<{
  /** Force the expanded rendering (mobile drawer). */
  forceExpanded?: boolean
}>(), { forceExpanded: false })

defineEmits<{ navigate: [] }>()

const { t } = useI18n()
const route = useRoute()
const navigationStore = useNavigationStore()
const { groups } = useNavigation()

const expanded = computed(() => props.forceExpanded || !navigationStore.sidebarCollapsed)
const collapsible = computed(() => !props.forceExpanded)

function isActive(item: NavItem): boolean {
  if (route.name === item.name) return true
  if (route.meta.breadcrumbParent === item.name) return true
  return route.path === item.path || route.path.startsWith(`${item.path}/`)
}
</script>
