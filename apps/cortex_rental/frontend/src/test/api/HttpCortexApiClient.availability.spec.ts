import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpCortexApiClient } from '@/api/adapters/HttpCortexApiClient'
import { HttpClient } from '@/api/adapters/httpClient'

describe('HttpCortexApiClient availability matrix', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('reads the whitelisted Frappe matrix method and maps ERP rows into the UI contract', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      message: { data: {
        starts_at: '2026-09-21 00:00:00',
        ends_at: '2026-09-27 23:59:59',
        items: [{
          item_code: 'CAM-01',
          item_name: 'Cinema Camera',
          category: 'Camera',
          is_serialized: true,
          fleet_quantity: 2,
          has_conflict: true,
          blocks: [{
            transaction: 'CRT-0001',
            rental_state: 'Contract',
            customer: 'Studio North',
            starts_at: '2026-09-22 09:00:00',
            ends_at: '2026-09-24 17:00:00',
            qty: 1
          }]
        }]
      } }
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    const client = new HttpCortexApiClient(new HttpClient({ baseUrl: '/api/method' }))

    const result = await client.getAvailabilityMatrix({
      start_date: '2026-09-21',
      end_date: '2026-09-27',
      view_mode: 'week',
      category: 'Camera',
      search: 'cinema'
    })

    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/method/cortex_rental.api.v1.availability.get_matrix?')
    expect(result.provenance).toBe('api')
    expect(result.rows[0]).toMatchObject({ item_code: 'CAM-01', total_fleet: 2, is_serialized: true })
    expect(result.rows[0].blocks?.[0]).toMatchObject({
      rental_id: 'CRT-0001',
      customer_name: 'Studio North',
      state: 'Contract',
      is_conflict: true
    })
  })
})
