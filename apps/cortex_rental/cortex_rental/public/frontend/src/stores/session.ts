import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { i18n, type LocaleType } from '@/app/i18n'

export interface UserCompany {
  id: string
  name: string
  code: string
  is_default?: boolean
  timezone?: string
  currency?: string
}

export interface UserProfile {
  id: string
  email: string
  full_name: string
  roles: string[]
  permissions: string[]
  avatar_url?: string
}

export const useSessionStore = defineStore('session', () => {
  // Session State
  const currentUser = ref<UserProfile | null>({
    id: 'DEMO-USR-001',
    email: 'kael@cortex.local',
    full_name: 'Kael Tremblay',
    roles: ['Operations Manager', 'System Manager'],
    permissions: [
      'cortex:operations:view',
      'cortex:availability:view',
      'cortex:rental:view',
      'cortex:quote:create',
      'cortex:checkout:perform',
      'cortex:checkin:perform',
      'cortex:approvals:decide',
      'cortex:catalog:view',
      'cortex:catalog:manage',
      'cortex:serial:view',
      'cortex:consignment:view',
      'cortex:consignment:finance',
      'cortex:intake:view',
      'cortex:drafts:review',
      'cortex:telemetry:admin',
      'cortex:copilot:access',
      'cortex:policies:view',
      'cortex:team:manage',
      'cortex:migration:run',
      'cortex:audit:view'
    ]
  })

  const userCompanies = ref<UserCompany[]>([
    {
      id: 'DEMO-COMP-001',
      name: 'Cortex Cinema Rentals',
      code: 'CINEMA-MTL',
      is_default: true,
      timezone: 'America/Toronto',
      currency: 'CAD'
    },
    {
      id: 'DEMO-COMP-002',
      name: 'Cortex Broadcast Montréal',
      code: 'BROADCAST-MTL',
      is_default: false,
      timezone: 'America/Toronto',
      currency: 'CAD'
    }
  ])

  const activeCompanyId = ref<string>('DEMO-COMP-001')
  const locale = ref<LocaleType>(
    (typeof localStorage !== 'undefined' && localStorage.getItem('cortex_locale') as LocaleType) || 'fr-CA'
  )
  const isAuthenticated = ref<boolean>(true)
  const isLoadingSession = ref<boolean>(false)

  // Getters
  const activeCompany = computed<UserCompany | undefined>(() => {
    return userCompanies.value.find(c => c.id === activeCompanyId.value) || userCompanies.value[0]
  })

  const hasMultipleCompanies = computed<boolean>(() => {
    return userCompanies.value.length > 1
  })

  const userRoles = computed<string[]>(() => {
    return currentUser.value?.roles || []
  })

  const hasPermission = (permission: string): boolean => {
    if (!currentUser.value) return false
    if (currentUser.value.roles.includes('System Manager') || currentUser.value.roles.includes('Administrator')) {
      return true
    }
    return currentUser.value.permissions.includes(permission)
  }

  const hasRole = (role: string): boolean => {
    return currentUser.value?.roles.includes(role) || false
  }

  // Actions
  const switchCompany = async (companyId: string): Promise<boolean> => {
    const target = userCompanies.value.find(c => c.id === companyId)
    if (!target) {
      console.error(`[Cortex Security] Attempted unauthorized company switch to ${companyId}`)
      return false
    }

    isLoadingSession.value = true
    try {
      activeCompanyId.value = target.id
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('cortex_active_company_id', target.id)
      }
      return true
    } finally {
      isLoadingSession.value = false
    }
  }

  const setLocale = (newLocale: LocaleType) => {
    locale.value = newLocale
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cortex_locale', newLocale)
    }
    i18n.global.locale.value = newLocale
  }

  const initializeSession = async () => {
    isLoadingSession.value = true
    try {
      const savedCompany = typeof localStorage !== 'undefined' ? localStorage.getItem('cortex_active_company_id') : null
      if (savedCompany && userCompanies.value.some(c => c.id === savedCompany)) {
        activeCompanyId.value = savedCompany
      }
      isAuthenticated.value = true
    } finally {
      isLoadingSession.value = false
    }
  }

  const logout = () => {
    isAuthenticated.value = false
    currentUser.value = null
  }

  return {
    currentUser,
    userCompanies,
    activeCompanyId,
    locale,
    isAuthenticated,
    isLoadingSession,
    activeCompany,
    hasMultipleCompanies,
    userRoles,
    hasPermission,
    hasRole,
    can: hasPermission,
    switchCompany,
    setLocale,
    initializeSession,
    logout
  }
})
