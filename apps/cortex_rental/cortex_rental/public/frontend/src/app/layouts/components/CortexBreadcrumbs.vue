<template>
  <nav aria-label="Breadcrumb" class="flex items-center space-x-1.5 text-xs text-cortex-text-muted">
    <ol class="flex items-center space-x-1.5 list-none m-0 p-0">
      <li
        v-for="(crumb, index) in breadcrumbs"
        :key="index"
        class="flex items-center space-x-1.5"
      >
        <ChevronRight
          v-if="index > 0"
          class="w-3.5 h-3.5 text-cortex-ink-200 flex-shrink-0"
          aria-hidden="true"
        />

        <RouterLink
          v-if="crumb.to && index < breadcrumbs.length - 1"
          :to="crumb.to"
          class="hover:text-cortex-primary-600 transition-colors truncate max-w-[140px] md:max-w-[200px]"
        >
          {{ getLabel(crumb) }}
        </RouterLink>

        <span
          v-else
          class="font-medium text-cortex-text-primary truncate max-w-[160px] md:max-w-[240px]"
          :aria-current="index === breadcrumbs.length - 1 ? 'page' : undefined"
        >
          {{ getLabel(crumb) }}
        </span>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ChevronRight } from 'lucide-vue-next'
import { useNavigationStore, type BreadcrumbItem } from '@/stores/navigation'

const { t, te } = useI18n()
const navigationStore = useNavigationStore()

const breadcrumbs = computed<BreadcrumbItem[]>(() => navigationStore.breadcrumbs)

const getLabel = (crumb: BreadcrumbItem): string => {
  if (crumb.labelKey) {
    if (te(crumb.labelKey)) {
      return t(crumb.labelKey)
    }
    return crumb.labelKey
  }
  return crumb.label || ''
}
</script>
