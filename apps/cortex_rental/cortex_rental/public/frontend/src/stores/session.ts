import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { i18n, type LocaleType } from '@/app/i18n'

export interface UserCompany { id: string; name: string; code: string; is_default?: boolean; timezone?: string; currency?: string }
export interface UserProfile { id: string; email: string; full_name: string; roles: string[]; permissions: string[]; avatar_url?: string }

export const useSessionStore = defineStore('session', () => {
  const currentUser = ref<UserProfile | null>(null)
  const userCompanies = ref<UserCompany[]>([])
  const activeCompanyId = ref('')
  const locale = ref<LocaleType>((typeof localStorage !== 'undefined' && localStorage.getItem('cortex_locale') as LocaleType) || 'fr-CA')
  const isAuthenticated = ref(false)
  const isLoadingSession = ref(false)
  let sessionRequest: Promise<boolean> | null = null
  const activeCompany = computed(() => userCompanies.value.find(c => c.id === activeCompanyId.value) || userCompanies.value[0])
  const hasMultipleCompanies = computed(() => userCompanies.value.length > 1)
  const userRoles = computed(() => currentUser.value?.roles || [])
  const hasPermission = (permission: string) => Boolean(currentUser.value && (currentUser.value.roles.some(r => ['System Manager', 'Administrator'].includes(r)) || currentUser.value.permissions.includes(permission)))
  const hasRole = (role: string) => currentUser.value?.roles.includes(role) || false

  const switchCompany = async (companyId: string) => {
    if (!userCompanies.value.some(c => c.id === companyId)) {
      console.error(`[Cortex Security] Attempted unauthorized company switch to ${companyId}`)
      return false
    }
    activeCompanyId.value = companyId
    if (typeof localStorage !== 'undefined') localStorage.setItem('cortex_active_company_id', companyId)
    return true
  }
  const setLocale = (newLocale: LocaleType) => {
    locale.value = newLocale
    if (typeof localStorage !== 'undefined') localStorage.setItem('cortex_locale', newLocale)
    i18n.global.locale.value = newLocale
  }
  const initializeSession = () => {
    if (isAuthenticated.value) return Promise.resolve(true)
    if (sessionRequest) return sessionRequest
    isLoadingSession.value = true
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 8000)
    sessionRequest = (async () => {
      try {
        const response = await fetch('/api/method/cortex_rental.api.v1.session.get_session_context', {
          credentials: 'include',
          signal: controller.signal
        })
        if (!response.ok) throw new Error('Frappe session unavailable')
        const envelope = await response.json()
        const context = envelope?.message?.data || envelope?.message || envelope?.data
        if (!context?.user?.id) throw new Error('Frappe returned no user context')
        const permissions = Object.entries(context.permissions || {}).filter(([, allowed]) => allowed === true).map(([permission]) => permission)
        currentUser.value = { ...context.user, permissions }
        userCompanies.value = context.companies || []
        const saved = typeof localStorage !== 'undefined' ? localStorage.getItem('cortex_active_company_id') : null
        activeCompanyId.value = userCompanies.value.some(c => c.id === saved) ? saved! : context.active_company_id || userCompanies.value[0]?.id || ''
        if (activeCompanyId.value && typeof localStorage !== 'undefined') localStorage.setItem('cortex_active_company_id', activeCompanyId.value)
        isAuthenticated.value = true
        return true
      } catch {
        currentUser.value = null
        userCompanies.value = []
        activeCompanyId.value = ''
        isAuthenticated.value = false
        return false
      } finally {
        clearTimeout(timeout)
        isLoadingSession.value = false
        sessionRequest = null
      }
    })()
    return sessionRequest
  }
  const logout = () => {
    isAuthenticated.value = false; currentUser.value = null; userCompanies.value = []; activeCompanyId.value = ''
    void fetch('/api/method/logout', { method: 'POST', credentials: 'include' })
  }
  return { currentUser, userCompanies, activeCompanyId, locale, isAuthenticated, isLoadingSession, activeCompany, hasMultipleCompanies, userRoles, hasPermission, hasRole, can: hasPermission, switchCompany, setLocale, initializeSession, logout }
})
