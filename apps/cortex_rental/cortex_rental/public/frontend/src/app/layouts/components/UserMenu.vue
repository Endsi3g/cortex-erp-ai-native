<template>
  <Dropdown :options="options" placement="right">
    <button type="button" class="flex items-center gap-2 rounded-lg pl-1 pr-1.5 py-1 hover:bg-cortex-surface-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-cortex-primary-500" :aria-label="`Menu du compte : ${fullName}`" data-test="user-menu">
      <span class="flex items-center justify-center w-8 h-8 rounded-full bg-cortex-ink-900 text-white text-xs font-semibold shadow-xs" aria-hidden="true">{{ initials }}</span>
      <span v-if="!compact" class="hidden lg:flex flex-col text-left">
        <span class="text-xs font-semibold text-cortex-text-primary leading-tight">{{ fullName }}</span>
        <span class="text-[11px] text-cortex-text-muted leading-tight">{{ primaryRole }}</span>
      </span>
    </button>
  </Dropdown>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { Dropdown } from 'frappe-ui'
import { LayoutGrid, LogOut, UserRound } from 'lucide-vue-next'
import { useSessionStore } from '@/stores/session'

defineProps<{ compact?: boolean }>()

const session = useSessionStore()
const fullName = computed(() => session.currentUser?.full_name || session.currentUser?.email || 'Compte Cortex')
const primaryRole = computed(() => session.currentUser?.roles.find((role) => !['All', 'Guest', 'Desk User'].includes(role)) || '')
const initials = computed(() =>
  fullName.value
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
)

// The Desk stays available for administration; sign-out ends the server session, then reloads on the sign-in screen.
const options = computed(() => [
  { label: 'Mon profil', icon: () => h(UserRound, { size: 16 }), onClick: () => window.location.assign('/me') },
  { label: 'Ouvrir le Desk', icon: () => h(LayoutGrid, { size: 16 }), onClick: () => window.location.assign('/app') },
  { label: 'Se déconnecter', icon: () => h(LogOut, { size: 16 }), onClick: () => session.logout() }
])
</script>
