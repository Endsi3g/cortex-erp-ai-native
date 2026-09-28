import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpCortexApiClient } from '@/api/adapters/HttpCortexApiClient'
import { HttpClient, CortexUnavailableError } from '@/api/adapters/httpClient'

// Every screen must call a whitelisted Frappe method that exists in cortex_rental/api/v1,
// never an invented REST path (the audit of 2026-09-28 found several).
const reply = (data: unknown) => new Response(JSON.stringify({ message: { data } }), { status: 200, headers: { 'Content-Type': 'application/json' } })

describe('HttpCortexApiClient endpoints', () => {
  afterEach(() => vi.unstubAllGlobals())

  const calls: Array<[string, (c: HttpCortexApiClient) => Promise<unknown>, string]> = [
    ['operations', (c) => c.getOperationsOverview(), 'operations.get_operations_overview'],
    ['equipment list', (c) => c.listEquipment({ page: 1, page_size: 20 }), 'catalog.list_equipment'],
    ['equipment', (c) => c.getEquipment({ item_code: 'CAM-1' }), 'catalog.get_equipment'],
    ['serial', (c) => c.getSerial({ serial_number: 'SN-1' }), 'catalog.get_serial'],
    ['kits', (c) => c.listKits({}), 'catalog.list_kits'],
    ['owners', (c) => c.listOwners({}), 'consignment.list_owners'],
    ['dashboard', (c) => c.getConsignmentDashboard({}), 'consignment.get_consignment_dashboard'],
    ['statement', (c) => c.getOwnerStatement({ owner_id: 'OWN-A', period: '2026-09' }), 'consignment.get_owner_statement'],
    ['inbound', (c) => c.listInboundRequests({}), 'intelligence.list_inbound_requests'],
    ['drafts', (c) => c.listAiDrafts({}), 'intelligence.list_ai_drafts'],
    ['activity', (c) => c.getAgentActivity({ limit: 10 }), 'intelligence.get_agent_activity'],
    ['audit', (c) => c.listAuditEvents({ page: 1, page_size: 20 }), 'intelligence.list_audit_events']
  ]

  it.each(calls)('%s calls a whitelisted cortex_rental method', async (_name, run, method) => {
    const fetchMock = vi.fn().mockResolvedValue(reply({ items: [] }))
    vi.stubGlobal('fetch', fetchMock)
    await run(new HttpCortexApiClient(new HttpClient({ baseUrl: '/api/method' })))
    expect(String(fetchMock.mock.calls[0][0])).toContain(`/api/method/cortex_rental.api.v1.${method}`)
  })

  it('reports features without a server endpoint as unavailable instead of faking success', async () => {
    const client = new HttpCortexApiClient(new HttpClient({ baseUrl: '/api/method' }))
    vi.stubGlobal('fetch', vi.fn())
    await expect(client.requestOwnerStatementExport({ owner_id: 'OWN-A', period: '2026-09', format: 'pdf' })).rejects.toBeInstanceOf(CortexUnavailableError)
    await expect(client.createUploadIntent({ file_name: 'a.jpg', file_size_bytes: 1, mime_type: 'image/jpeg', purpose: 'damage_photo' })).rejects.toBeInstanceOf(CortexUnavailableError)
    await expect(client.listRentalPolicies({})).rejects.toBeInstanceOf(CortexUnavailableError)
    expect(fetch).not.toHaveBeenCalled()
  })
})
