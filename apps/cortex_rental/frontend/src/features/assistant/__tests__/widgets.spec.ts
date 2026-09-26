import { describe, expect, it } from 'vitest'
import { widgetModel } from '../widgets'
import { embedUrl } from '../artifacts'

const t = (key: string, values?: Record<string, unknown>) => (values ? `${key}:${JSON.stringify(values)}` : key)

describe('assistant widgets', () => {
  it('turns a rentals page into a table linked to each rental and to the list', () => {
    const model = widgetModel('list_rentals', { type: 'table', entity: 'rentals' }, {
      items: [{ name: 'TRX-1', customer_name: 'Nord', rental_state: 'Reservation', starts_at: '2026-09-10 08:00:00', grand_total: 1200, currency: 'CAD' }],
      total_count: 7
    }, t, 'fr-CA')!
    expect(model.route).toBe('/rentals')
    expect(model.subtitle).toContain('"count":7')
    expect(model.rows![0]!.route).toBe('/rentals/TRX-1')
    expect(model.rows![0]!.cells[2]!.text).toBe('rental_states.Reservation')
  })

  it('flags unavailable items and offers a prefilled quote', () => {
    const model = widgetModel('check_availability', { type: 'availability', items: ['ALEXA', 'LENS'], starts_at: '2026-10-01T08:00', ends_at: '2026-10-04T18:00' }, [
      { item_id: 'ALEXA', requested_quantity: 2, available_quantity: 1, total_fleet_quantity: 3, is_available: false },
      { item_id: 'LENS', requested_quantity: 1, available_quantity: 4, total_fleet_quantity: 4, is_available: true }
    ], t, 'fr-CA')!
    expect(model.rows!.map(r => r.cells[3]!.tone)).toEqual(['red', 'green'])
    expect(model.action!.route).toBe('/rentals/new?items=ALEXA%2CLENS&starts_at=2026-10-01&ends_at=2026-10-04')
  })

  it('shows the P&L refusal reason instead of zeros', () => {
    const model = widgetModel('profit_and_loss', { type: 'report', entity: 'pnl' }, { available: false, reason: 'Aucun exercice' }, t, 'fr-CA')!
    expect(model.subtitle).toBe('Aucun exercice')
    expect(model.tiles).toEqual([])
  })

  it('ignores unknown widgets', () => {
    expect(widgetModel('x', { type: 'table', entity: 'nope' }, [], t, 'fr-CA')).toBeNull()
  })

  it('builds embed URLs for the artifact panel', () => {
    expect(embedUrl('/rentals/TRX-1', '/cortex/')).toBe('/cortex/rentals/TRX-1?embed=1')
    expect(embedUrl('/availability?from=2026-10-01', '/cortex/')).toBe('/cortex/availability?from=2026-10-01&embed=1')
    expect(embedUrl('/operations', '/preview/')).toBe('/preview/?route=%2Foperations%3Fembed%3D1')
  })
})
