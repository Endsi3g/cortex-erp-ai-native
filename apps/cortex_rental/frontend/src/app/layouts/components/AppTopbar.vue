<template>
  <!--
    ERPNext top bar (inspiration/image.png): 48px (47 + 1px border), module
    breadcrumb at 16px, 300×28 search field, bell, Help, 28px avatar, 16px
    right gutter.
  -->
  <header class="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-outline-gray-1 bg-surface-white pl-4 pr-4 print:hidden">
    <div class="flex min-w-0 items-center gap-2">
      <button
        type="button"
        class="-ml-1 flex size-7 items-center justify-center rounded text-ink-gray-7 hover:bg-surface-gray-2 md:hidden"
        :aria-label="t('common.navigation.open_menu')"
        @click="$emit('open-menu')"
      >
        <Menu class="size-4" :stroke-width="1.5" />
      </button>
      <nav :aria-label="t('common.navigation.breadcrumbs')" class="min-w-0">
        <ol class="flex min-w-0 items-center gap-1.5 text-base text-ink-gray-8">
          <li v-for="(crumb, index) in navigationStore.breadcrumbs" :key="index" class="flex min-w-0 items-center gap-1.5">
            <span v-if="index > 0" class="text-ink-gray-4" aria-hidden="true">/</span>
            <RouterLink v-if="crumb.to" :to="crumb.to" class="truncate hover:text-ink-gray-9">{{ crumb.labelKey ? t(crumb.labelKey) : crumb.label }}</RouterLink>
            <span v-else class="truncate">{{ crumb.labelKey ? t(crumb.labelKey) : crumb.label }}</span>
          </li>
        </ol>
      </nav>
    </div>

    <div class="flex shrink-0 items-center">
      <button
        type="button"
        class="hidden h-7 w-[300px] items-center gap-2 rounded bg-surface-gray-2 px-2 text-left text-base text-ink-gray-4 outline-none hover:bg-surface-gray-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3 lg:flex"
        aria-keyshortcuts="Meta+K Control+K"
        @click="navigationStore.openUniversalSearch()"
      >
        <Search class="size-4 shrink-0 text-ink-gray-6" :stroke-width="1.5" aria-hidden="true" />
        <span class="truncate">{{ t('common.navigation.search_placeholder') }}</span>
      </button>
      <button
        type="button"
        class="flex size-7 items-center justify-center rounded text-ink-gray-7 hover:bg-surface-gray-2 lg:hidden"
        :aria-label="t('common.navigation.search_placeholder')"
        @click="navigationStore.openUniversalSearch()"
      >
        <Search class="size-4" :stroke-width="1.5" />
      </button>

      <div class="ml-6 flex items-center gap-2.5">
        <Dropdown :options="notificationOptions" align="end">
          <button
            type="button"
            class="relative flex size-7 items-center justify-center rounded text-ink-gray-7 hover:bg-surface-gray-2"
            :aria-label="notificationLabel"
          >
            <Bell class="size-4" :stroke-width="1.5" />
            <span
              v-if="approvalsStore.pendingCount"
              class="absolute right-1 top-1 size-1.5 rounded-full bg-surface-red-5"
              aria-hidden="true"
            />
          </button>
        </Dropdown>

        <Tooltip :text="t('copilot.open_shortcut')">
          <button
            type="button"
            class="flex size-7 items-center justify-center rounded text-ink-gray-7 hover:bg-surface-gray-2"
            :aria-label="t('copilot.open_shortcut')"
            aria-keyshortcuts="Meta+J Control+J"
            @click="copilotStore.toggle()"
          >
            <Sparkles class="size-4" :stroke-width="1.5" />
          </button>
        </Tooltip>

        <Dropdown :options="helpOptions" align="end">
          <button type="button" class="flex h-7 items-center gap-1 rounded px-2 text-base text-ink-gray-8 hover:bg-surface-gray-2">
            {{ t('common.navigation.help') }}
            <ChevronDown class="size-3.5 text-ink-gray-6" :stroke-width="1.5" aria-hidden="true" />
          </button>
        </Dropdown>

        <Dropdown :options="accountOptions" align="end">
          <button type="button" class="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3" :aria-label="t('common.navigation.account_menu')">
            <Avatar size="lg" shape="circle" :label="sessionStore.currentUser?.full_name || sessionStore.currentUser?.email || '?'" :image="sessionStore.currentUser?.avatar_url" />
          </button>
        </Dropdown>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { Avatar, Dropdown, Tooltip } from 'frappe-ui'
import { Bell, Building2, ChevronDown, ExternalLink, Keyboard, Languages, LogOut, Menu, Search, Sparkles } from 'lucide-vue-next'
import { useSessionStore } from '@/stores/session'
import { useNavigationStore } from '@/stores/navigation'
import { useApprovalsStore } from '@/stores/approvals'
import { useCopilotStore } from '@/stores/copilot'

defineEmits<{ 'open-menu': [] }>()

const { t } = useI18n()
const router = useRouter()
const sessionStore = useSessionStore()
const navigationStore = useNavigationStore()
const approvalsStore = useApprovalsStore()
const copilotStore = useCopilotStore()

onMounted(() => {
  if (sessionStore.hasPermission('cortex:approvals:decide')) void approvalsStore.fetchPendingApprovals()
})

const notificationLabel = computed(() =>
  approvalsStore.pendingCount
    ? t('common.navigation.pending_approvals', { count: approvalsStore.pendingCount })
    : t('common.navigation.notifications')
)

const notificationOptions = computed(() => {
  if (!sessionStore.hasPermission('cortex:approvals:decide')) {
    return [{ label: t('common.navigation.no_notifications'), disabled: true }]
  }
  if (approvalsStore.pendingCount === null) {
    return [{ label: t('common.navigation.notifications_unavailable'), disabled: true }]
  }
  return [
    {
      label: approvalsStore.pendingCount
        ? t('common.navigation.pending_approvals', { count: approvalsStore.pendingCount })
        : t('common.navigation.no_pending_approvals'),
      onClick: () => router.push({ name: 'ai-inbox', query: { type: 'approval' } })
    }
  ]
})

const helpOptions = computed(() => [
  {
    label: sessionStore.locale === 'fr-CA' ? 'English' : 'Français',
    icon: Languages,
    onClick: () => sessionStore.setLocale(sessionStore.locale === 'fr-CA' ? 'en-CA' : 'fr-CA')
  },
  { label: t('common.navigation.keyboard_shortcuts'), icon: Keyboard, onClick: () => navigationStore.openUniversalSearch() },
  { label: t('common.navigation.open_erpnext'), icon: ExternalLink, onClick: () => window.open('/app', '_blank', 'noopener') }
])

const accountOptions = computed(() => [
  {
    group: sessionStore.currentUser?.full_name || sessionStore.currentUser?.email || '',
    items: sessionStore.userCompanies.map(company => ({
      label: company.name,
      icon: Building2,
      selected: company.id === sessionStore.activeCompanyId,
      onClick: () => void sessionStore.switchCompany(company.id).then(() => router.go(0))
    }))
  },
  {
    group: 'session',
    hideLabel: true,
    items: [{ label: t('common.navigation.logout'), icon: LogOut, onClick: logout }]
  }
])

function logout() {
  sessionStore.logout()
  window.location.href = '/api/method/web_logout'
}
</script>
