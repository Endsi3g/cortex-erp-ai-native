/**
 * Read-tool results → what the conversation shows (tables, records, KPI
 * tiles, lines). Pure: tested without rendering. Every widget links to the
 * real Cortex page it summarizes; nothing here computes business numbers,
 * it only formats what the endpoint returned.
 */
import type { WidgetView } from '@/api/contracts/ai'
import { formatDate, formatDateTime, formatMoney } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

type Translate = (key: string, values?: Record<string, unknown>) => string
type Tone = 'green' | 'red' | 'orange' | 'gray'
type Row = Record<string, unknown>

export interface Cell { text: string; tone?: Tone; mono?: boolean; align?: 'right' }
export interface WidgetModel {
  icon: 'table' | 'record' | 'kpis' | 'availability' | 'pricing' | 'report'
  title: string
  subtitle?: string
  columns?: Array<{ label: string; align?: 'right' }>
  rows?: Array<{ cells: Cell[]; route?: string }>
  fields?: Array<{ label: string; value: Cell }>
  tiles?: Array<{ label: string; value: string; tone?: Tone }>
  footer?: Array<{ label: string; value: string; strong?: boolean }>
  /** The page this widget summarizes (opened in the artifact panel or navigated to). */
  route: string
  routeLabel: string
  /** Optional follow-up (e.g. open the composer prefilled). */
  action?: { label: string; route: string }
}

const obj = (value: unknown): Row => (value && typeof value === 'object' && !Array.isArray(value) ? (value as Row) : {})
const list = (value: unknown): Row[] => (Array.isArray(value) ? (value as Row[]) : Array.isArray(obj(value).items) ? (obj(value).items as Row[]) : [])
const str = (value: unknown) => (value === null || value === undefined || value === '' ? '—' : String(value))
const num = (value: unknown) => (typeof value === 'number' ? value : Number(value ?? 0))
const q = (params: Record<string, string | undefined>) => {
  const search = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as Array<[string, string]>).toString()
  return search ? `?${search}` : ''
}

export function widgetModel(_tool: string, view: WidgetView, data: unknown, t: Translate, locale: LocaleType): WidgetModel | null {
  const money = (value: unknown, currency?: unknown) => formatMoney(num(value), (currency as string) ?? null, locale)
  const date = (value: unknown) => (value ? formatDate(String(value), locale) : '—')
  const stamp = (value: unknown) => (value ? formatDateTime(String(value), locale) : '—')
  const state = (value: unknown) => t(`rental_states.${str(value)}`)
  const items = list(data)
  const total = num(obj(data).total_count) || items.length
  const count = t('ai.widget.results', { count: total })

  switch (view.entity ?? view.type) {
    case 'customers':
      return {
        icon: 'table', title: t('ai.widget.customers'), subtitle: count, route: '/customers', routeLabel: t('ai.widget.open_list'),
        columns: [{ label: t('ai.widget.name') }, { label: t('ai.widget.email') }, { label: t('ai.widget.active'), align: 'right' }, { label: t('ai.widget.outstanding'), align: 'right' }],
        rows: items.map(r => ({ route: `/customers/${encodeURIComponent(str(r.name))}`, cells: [{ text: str(r.customer_name) }, { text: str(r.email) }, { text: str(r.active_rentals), align: 'right' }, { text: money(r.outstanding), align: 'right', tone: num(r.outstanding) > 0 ? 'orange' : undefined }] }))
      }
    case 'equipment':
      if (view.type === 'record') {
        const d = obj(data), fleet = obj(d.fleet)
        return {
          icon: 'record', title: str(d.item_name), subtitle: str(d.item_code), route: `/equipment/${encodeURIComponent(str(d.item_code))}`, routeLabel: t('ai.widget.open_record'),
          fields: [
            { label: t('ai.widget.category'), value: { text: str(d.category) } },
            { label: t('ai.widget.daily_rate'), value: { text: money(d.daily_rate, d.currency) } },
            { label: t('ai.widget.replacement_value'), value: { text: money(d.replacement_value, d.currency) } },
            { label: t('ai.widget.fleet'), value: { text: t('ai.widget.fleet_value', { active: num(fleet.active), total: num(fleet.total), out: num(fleet.out) }) } }
          ]
        }
      }
      return {
        icon: 'table', title: t('ai.widget.equipment'), subtitle: count, route: '/equipment', routeLabel: t('ai.widget.open_list'),
        columns: [{ label: t('ai.widget.code') }, { label: t('ai.widget.name') }, { label: t('ai.widget.daily_rate'), align: 'right' }, { label: t('ai.widget.fleet'), align: 'right' }],
        rows: items.map(r => ({ route: `/equipment/${encodeURIComponent(str(r.item_code))}`, cells: [{ text: str(r.item_code), mono: true }, { text: str(r.item_name) }, { text: money(r.daily_rate, r.currency), align: 'right' }, { text: `${num(r.fleet_active)}/${num(r.fleet_total)}`, align: 'right' }] }))
      }
    case 'rentals':
      return {
        icon: 'table', title: t('ai.widget.rentals'), subtitle: count, route: '/rentals', routeLabel: t('ai.widget.open_list'),
        columns: [{ label: t('ai.widget.rental') }, { label: t('ai.widget.customer') }, { label: t('ai.widget.state') }, { label: t('ai.widget.start') }, { label: t('ai.widget.total'), align: 'right' }],
        rows: items.map(r => ({ route: `/rentals/${encodeURIComponent(str(r.name))}`, cells: [{ text: str(r.name), mono: true }, { text: str(r.customer_name) }, { text: state(r.rental_state) }, { text: date(r.starts_at) }, { text: money(r.grand_total, r.currency), align: 'right' }] }))
      }
    case 'rental': {
      const d = obj(data)
      return {
        icon: 'record', title: str(d.name || d.id), subtitle: `${str(d.customer_name)} · ${state(d.rental_state)}`, route: `/rentals/${encodeURIComponent(str(d.id || d.name))}`, routeLabel: t('ai.widget.open_record'),
        fields: [
          { label: t('ai.widget.period'), value: { text: `${stamp(d.starts_at)} → ${stamp(d.ends_at)}` } },
          { label: t('ai.widget.lines'), value: { text: String(list(d.items).length) } },
          { label: t('ai.widget.billable_days'), value: { text: str(d.billable_days) } },
          { label: t('ai.widget.total'), value: { text: money(d.grand_total, d.currency) } }
        ]
      }
    }
    case 'rental_billing': {
      const d = obj(data), advance = obj(d.advance), invoice = obj(d.final_invoice)
      return {
        icon: 'record', title: t('ai.widget.billing_of', { id: str(view.id) }), route: `/rentals/${encodeURIComponent(str(view.id))}`, routeLabel: t('ai.widget.open_record'),
        fields: [
          { label: t('ai.widget.advance_requested'), value: { text: money(advance.requested, d.currency) } },
          { label: t('ai.widget.advance_received'), value: { text: money(advance.received, d.currency), tone: advance.covered ? 'green' : 'orange' } },
          { label: t('ai.widget.final_invoice'), value: { text: d.final_invoice ? `${str(invoice.name)} · ${str(invoice.status)}` : t('ai.widget.none') } },
          { label: t('ai.widget.outstanding'), value: { text: d.final_invoice ? money(invoice.outstanding_amount, d.currency) : '—' } }
        ]
      }
    }
    case 'customer': {
      const d = obj(data), stats = obj(d.stats), insurance = obj(d.insurance)
      return {
        icon: 'record', title: str(d.customer_name), subtitle: str(d.email), route: `/customers/${encodeURIComponent(str(d.name))}`, routeLabel: t('ai.widget.open_record'),
        fields: [
          { label: t('ai.widget.active'), value: { text: str(stats.active_rentals) } },
          { label: t('ai.widget.rentals'), value: { text: str(stats.rentals) } },
          { label: t('ai.widget.outstanding'), value: { text: money(stats.outstanding, d.currency), tone: num(stats.outstanding) > 0 ? 'orange' : undefined } },
          { label: t('ai.widget.insurance'), value: { text: t(`ai.widget.insurance_${str(insurance.status)}`), tone: insurance.status === 'valid' ? 'green' : insurance.status === 'expired' ? 'red' : 'gray' } }
        ]
      }
    }
    case 'invoices':
      return {
        icon: 'table', title: t('ai.widget.invoices'), subtitle: count, route: '/finance/invoices', routeLabel: t('ai.widget.open_list'),
        columns: [{ label: t('ai.widget.invoice') }, { label: t('ai.widget.customer') }, { label: t('ai.widget.status') }, { label: t('ai.widget.due') }, { label: t('ai.widget.outstanding'), align: 'right' }],
        rows: items.map(r => ({ route: r.cortex_rental_transaction ? `/rentals/${encodeURIComponent(str(r.cortex_rental_transaction))}` : undefined, cells: [{ text: str(r.name), mono: true }, { text: str(r.customer_name) }, { text: str(r.status), tone: r.status === 'Overdue' ? 'red' : r.status === 'Paid' ? 'green' : undefined }, { text: date(r.due_date) }, { text: money(r.outstanding_amount, r.currency), align: 'right' }] }))
      }
    case 'inbox':
      return {
        icon: 'table', title: t('ai.widget.inbox'), subtitle: count, route: '/ai/inbox', routeLabel: t('ai.widget.open_list'),
        columns: [{ label: t('ai.item') }, { label: t('ai.widget.customer') }, { label: t('ai.widget.state') }],
        rows: items.map(r => ({ route: `/ai/workspace/${encodeURIComponent(str(r.id))}`, cells: [{ text: str(r.title) }, { text: str(r.customer) }, { text: t(`ai.state_${str(r.state)}`) }] }))
      }
    case 'operations': {
      const k = obj(obj(data).kpis)
      return {
        icon: 'kpis', title: t('ai.widget.day', { day: date(obj(data).day) }), route: '/operations', routeLabel: t('ai.widget.open_page'),
        tiles: [
          { label: t('ai.widget.departures'), value: str(k.departures) },
          { label: t('ai.widget.returns'), value: str(k.returns) },
          { label: t('ai.widget.overdue'), value: str(k.overdue), tone: num(k.overdue) ? 'red' : undefined },
          { label: t('ai.widget.exceptions'), value: str(k.exceptions), tone: num(k.exceptions) ? 'orange' : undefined }
        ]
      }
    }
    case 'consignment': {
      const d = obj(data)
      return {
        icon: 'kpis', title: t('ai.widget.consignment'), route: '/consignment', routeLabel: t('ai.widget.open_page'),
        tiles: [
          { label: t('ai.widget.payout_month'), value: money(d.current_month_total_payout, d.currency) },
          { label: t('ai.widget.owners'), value: str(d.active_owners_count) },
          { label: t('ai.widget.consigned_serials'), value: str(d.active_consigned_serials_count) }
        ]
      }
    }
    case 'policies': {
      const d = obj(data), settings = obj(d.settings)
      return {
        icon: 'kpis', title: t('ai.widget.policies'), route: '/admin/policies', routeLabel: t('ai.widget.open_page'),
        tiles: [
          { label: t('ai.widget.advance'), value: `${num(settings.advance_percentage)} %` },
          { label: t('ai.widget.rules'), value: String(list(d.rules).length) },
          { label: t('ai.widget.week_billed'), value: str(list(d.curve).find(p => num(p.calendar_days) === 7)?.billable_days) }
        ]
      }
    }
    case 'owner_statement': {
      const totals = obj(obj(obj(data).statement).totals ?? obj(data).totals)
      return {
        icon: 'record', title: t('ai.widget.statement', { owner: str(view.id), period: str(view.period) }), route: `/consignment/owners/${encodeURIComponent(str(view.id))}/statement/${encodeURIComponent(str(view.period))}`, routeLabel: t('ai.widget.open_record'),
        fields: Object.entries(totals).map(([key, value]) => ({ label: key, value: { text: typeof value === 'number' ? money(value) : str(value) } }))
      }
    }
    case 'availability': {
      const codes = (view.items as string[] | undefined) ?? []
      const period = { starts_at: String(view.starts_at ?? '').slice(0, 10), ends_at: String(view.ends_at ?? '').slice(0, 10) }
      return {
        icon: 'availability', title: t('ai.widget.availability'), subtitle: `${date(view.starts_at)} → ${date(view.ends_at)}`, route: `/availability${q({ from: period.starts_at })}`, routeLabel: t('ai.widget.open_page'),
        columns: [{ label: t('ai.widget.code') }, { label: t('ai.widget.requested'), align: 'right' }, { label: t('ai.widget.available'), align: 'right' }, { label: t('ai.widget.status') }],
        rows: (Array.isArray(data) ? (data as Row[]) : []).map(r => ({
          route: `/equipment/${encodeURIComponent(str(r.item_id))}`,
          cells: [{ text: str(r.item_id), mono: true }, { text: str(r.requested_quantity), align: 'right' }, { text: `${num(r.available_quantity)} / ${num(r.total_fleet_quantity)}`, align: 'right' }, { text: r.is_available ? t('ai.widget.ok') : t('ai.widget.short'), tone: r.is_available ? 'green' : 'red' }]
        })),
        action: codes.length ? { label: t('ai.widget.start_quote'), route: `/rentals/new${q({ items: codes.join(','), ...period })}` } : undefined
      }
    }
    case 'pricing': {
      const d = obj(data), codes = (view.items as string[] | undefined) ?? []
      return {
        icon: 'pricing', title: t('ai.widget.pricing'), subtitle: t('ai.widget.billable', { calendar: str(d.calendar_days), billable: str(d.billable_days) }), route: `/rentals/new${q({ items: codes.join(','), starts_at: String(view.starts_at ?? '').slice(0, 10), ends_at: String(view.ends_at ?? '').slice(0, 10) })}`, routeLabel: t('ai.widget.start_quote'),
        columns: [{ label: t('ai.widget.name') }, { label: t('ai.widget.qty'), align: 'right' }, { label: t('ai.widget.daily_rate'), align: 'right' }, { label: t('ai.widget.total'), align: 'right' }],
        rows: list(d.lines).map(r => ({ cells: [{ text: str(r.item_name) }, { text: str(r.quantity), align: 'right' }, { text: money(r.daily_rate), align: 'right' }, { text: money(r.line_subtotal), align: 'right' }] })),
        footer: [
          { label: t('ai.widget.subtotal'), value: money(d.subtotal) },
          { label: d.tax_estimate_complete === false ? t('ai.widget.taxes_estimated') : t('ai.widget.taxes'), value: money(d.tax_amount) },
          { label: t('ai.widget.total'), value: money(d.grand_total), strong: true }
        ]
      }
    }
    case 'pnl': {
      const d = obj(data)
      if (d.available === false) {
        return { icon: 'report', title: t('ai.widget.pnl'), subtitle: str(d.reason), route: '/finance/profit-and-loss', routeLabel: t('ai.widget.open_page'), tiles: [] }
      }
      return {
        icon: 'report', title: t('ai.widget.pnl'), subtitle: `${date(view.from_date)} → ${date(view.to_date)}`, route: '/finance/profit-and-loss', routeLabel: t('ai.widget.open_page'),
        tiles: [
          { label: t('ai.widget.income'), value: money(d.totalIncome, d.currency) },
          { label: t('ai.widget.expense'), value: money(d.totalExpense, d.currency) },
          { label: t('ai.widget.net'), value: money(d.netProfit, d.currency), tone: num(d.netProfit) < 0 ? 'red' : 'green' }
        ]
      }
    }
    default:
      return null
  }
}
