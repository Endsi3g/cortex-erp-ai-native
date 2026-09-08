<template>
  <!-- Multi-tenant company switcher: rendered ONLY if user has > 1 authorized companies -->
  <div
    v-if="sessionStore.hasMultipleCompanies"
    class="relative"
    ref="dropdownRef"
  >
    <button
      type="button"
      @click="toggleDropdown"
      class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-cortex-border bg-cortex-surface text-cortex-text-primary text-xs font-medium hover:bg-cortex-surface-subtle transition-colors focus:outline-none focus:ring-2 focus:ring-cortex-primary-500 shadow-sm"
      :aria-expanded="isOpen"
      aria-haspopup="listbox"
      aria-label="Sélectionner la société active"
    >
      <Building2 class="w-3.5 h-3.5 text-cortex-primary-600 flex-shrink-0" />
      <span class="truncate max-w-[130px] md:max-w-[180px]">
        {{ sessionStore.activeCompany?.name || t('common.company') }}
      </span>
      <ChevronDown
        class="w-3 h-3 text-cortex-text-muted transition-transform duration-150"
        :class="{ 'rotate-180': isOpen }"
      />
    </button>

    <!-- Dropdown Menu -->
    <div
      v-if="isOpen"
      class="absolute right-0 mt-1.5 w-64 rounded-xl border border-cortex-border bg-cortex-surface shadow-lg z-50 p-1.5 animate-in fade-in zoom-in-95 duration-100"
      role="listbox"
      tabindex="-1"
    >
      <div class="px-2.5 py-1.5 text-[11px] font-semibold text-cortex-text-muted uppercase tracking-wider border-b border-cortex-border mb-1">
        {{ t('common.company') }} ({{ sessionStore.userCompanies.length }})
      </div>

      <button
        v-for="company in sessionStore.userCompanies"
        :key="company.id"
        type="button"
        @click="handleSelect(company.id)"
        role="option"
        :aria-selected="company.id === sessionStore.activeCompanyId"
        class="w-full flex items-start gap-2.5 px-2.5 py-2 rounded-lg text-left text-xs transition-colors"
        :class="[
          company.id === sessionStore.activeCompanyId
            ? 'bg-cortex-primary-50 text-cortex-primary-700 font-semibold'
            : 'text-cortex-text-primary hover:bg-cortex-surface-subtle'
        ]"
      >
        <Check
          v-if="company.id === sessionStore.activeCompanyId"
          class="w-4 h-4 text-cortex-primary-600 flex-shrink-0 mt-0.5"
        />
        <div v-else class="w-4 h-4 flex-shrink-0" />

        <div class="flex flex-col min-w-0">
          <span class="truncate">{{ company.name }}</span>
          <span class="text-[10px] text-cortex-text-muted font-mono font-normal">
            {{ company.code }} · {{ company.currency }}
          </span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Building2, ChevronDown, Check } from 'lucide-vue-next'
import { useSessionStore } from '@/stores/session'

const { t } = useI18n()
const router = useRouter()
const sessionStore = useSessionStore()

const isOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

const toggleDropdown = () => {
  isOpen.value = !isOpen.value
}

const handleSelect = async (companyId: string) => {
  if (companyId === sessionStore.activeCompanyId) {
    isOpen.value = false
    return
  }

  const success = await sessionStore.switchCompany(companyId)
  if (success) {
    isOpen.value = false
    // Reset route to operations cockpit to prevent cross-company stale state
    router.push('/app/cortex-operations')
  }
}

const handleClickOutside = (event: MouseEvent) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
