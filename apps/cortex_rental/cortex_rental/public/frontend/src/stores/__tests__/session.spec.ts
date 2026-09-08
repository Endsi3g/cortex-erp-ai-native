import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '@/stores/session'

describe('Session Store — Multi-Tenant & RBAC', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('S-TEST-1: Initializes with default synthetic multi-company session', () => {
    const sessionStore = useSessionStore()
    expect(sessionStore.isAuthenticated).toBe(true)
    expect(sessionStore.activeCompanyId).toBe('DEMO-COMP-001')
    expect(sessionStore.userCompanies.length).toBe(2)
    expect(sessionStore.hasMultipleCompanies).toBe(true)
  })

  it('S-TEST-2: Switches active company with authorization check', async () => {
    const sessionStore = useSessionStore()

    const switchSuccess = await sessionStore.switchCompany('DEMO-COMP-002')
    expect(switchSuccess).toBe(true)
    expect(sessionStore.activeCompanyId).toBe('DEMO-COMP-002')
    expect(sessionStore.activeCompany?.name).toBe('Cortex Broadcast Montréal')

    // Reject unauthorized company
    const unauthorizedSuccess = await sessionStore.switchCompany('COMP-UNAUTHORIZED-999')
    expect(unauthorizedSuccess).toBe(false)
    expect(sessionStore.activeCompanyId).toBe('DEMO-COMP-002')
  })

  it('S-TEST-3: Correctly validates RBAC permissions and system roles', () => {
    const sessionStore = useSessionStore()

    expect(sessionStore.hasPermission('cortex:operations:view')).toBe(true)
    expect(sessionStore.hasPermission('cortex:approvals:decide')).toBe(true)

    // Revoke system manager and restrict
    if (sessionStore.currentUser) {
      sessionStore.currentUser.roles = ['Warehouse Operator']
      sessionStore.currentUser.permissions = ['cortex:checkout:perform', 'cortex:checkin:perform']
    }

    expect(sessionStore.hasPermission('cortex:checkout:perform')).toBe(true)
    expect(sessionStore.hasPermission('cortex:approvals:decide')).toBe(false)
  })

  it('S-TEST-4: Updates locale between fr-CA and en-CA', () => {
    const sessionStore = useSessionStore()
    sessionStore.setLocale('en-CA')
    expect(sessionStore.locale).toBe('en-CA')

    sessionStore.setLocale('fr-CA')
    expect(sessionStore.locale).toBe('fr-CA')
  })
})
