import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '@/stores/session'

const context = { message: { data: {
  user: { id: 'operator@example.test', email: 'operator@example.test', full_name: 'Operator', roles: ['Warehouse Operator'] },
  companies: [{ id: 'Company A', name: 'Company A', code: 'Company A', is_default: true, currency: 'CAD' }, { id: 'Company B', name: 'Company B', code: 'Company B', currency: 'CAD' }],
  active_company_id: 'Company A', permissions: { 'cortex:checkout:perform': true, 'cortex:checkin:perform': true, 'cortex:approvals:decide': false }
} } }

describe('Session Store — Frappe authentication and RBAC', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(context), { status: 200 }))) })
  it('starts unauthenticated, then loads the live Frappe session context', async () => {
    const session = useSessionStore()
    expect(session.isAuthenticated).toBe(false)
    expect(await session.initializeSession()).toBe(true)
    expect(session.currentUser?.id).toBe('operator@example.test')
    expect(session.activeCompanyId).toBe('Company A')
    expect(session.userCompanies).toHaveLength(2)
  })
  it('shares one in-flight Frappe request between concurrent session guards', async () => {
    let resolveFetch!: (response: Response) => void
    const fetchMock = vi.fn(() => new Promise<Response>(resolve => { resolveFetch = resolve }))
    vi.stubGlobal('fetch', fetchMock)
    const session = useSessionStore()
    const first = session.initializeSession()
    const second = session.initializeSession()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    resolveFetch(new Response(JSON.stringify(context), { status: 200 }))
    await expect(Promise.all([first, second])).resolves.toEqual([true, true])
  })
  it('leaves the router able to show login when Frappe never responds', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn((_input: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    })))
    try {
      const session = useSessionStore()
      const pending = session.initializeSession()
      await vi.advanceTimersByTimeAsync(8000)
      await expect(pending).resolves.toBe(false)
      expect(session.isLoadingSession).toBe(false)
      expect(session.isAuthenticated).toBe(false)
    } finally { vi.useRealTimers() }
  })
  it('only permits switching to a company returned by Frappe', async () => {
    const session = useSessionStore(); await session.initializeSession()
    expect(await session.switchCompany('Company B')).toBe(true)
    expect(session.activeCompany?.name).toBe('Company B')
    expect(await session.switchCompany('unauthorized')).toBe(false)
    expect(session.activeCompanyId).toBe('Company B')
  })
  it('uses role and permission data returned by Frappe for authorization', async () => {
    const session = useSessionStore(); await session.initializeSession()
    expect(session.hasPermission('cortex:checkout:perform')).toBe(true)
    expect(session.hasPermission('cortex:approvals:decide')).toBe(false)
  })
  it('updates locale between fr-CA and en-CA', () => {
    const session = useSessionStore(); session.setLocale('en-CA'); expect(session.locale).toBe('en-CA')
    session.setLocale('fr-CA'); expect(session.locale).toBe('fr-CA')
  })
})
