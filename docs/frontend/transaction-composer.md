# Cortex Transaction Composer

`/app/cortex-transaction-composer` — the second of the three screens
the design spec calls out as the ones that "make it obvious an
operator can work faster in Cortex than in a legacy ERP" (Disponibilité
done, Composer this wave, Check-in next). Same packaging convention as
every other Cortex page: plain Vue 3 SFC under `public/js/`, no
npm/Vite project, native Frappe Desk Page.

## Files

```
apps/cortex_rental/cortex_rental/cortex_rental/page/cortex_transaction_composer/
└── cortex_transaction_composer.json / .js

apps/cortex_rental/cortex_rental/public/js/cortex_transaction_composer/
├── CortexTransactionComposer.vue
└── cortex_transaction_composer.bundle.js

apps/cortex_rental/cortex_rental/public/js/cortex_shared/
└── dateUtils.js   # fmtDateTime/addDays, extracted here once a second
                    # page (this one) needed the exact same helper
                    # CortexAvailability.vue already had
```

## Backend it's built on — all pre-existing except one new endpoint

| Endpoint | New this wave? | Notes |
|---|---|---|
| `customers.search_customers` | No | Already existed, agent-scoped |
| `customers.create_customer_draft` | No | Already existed |
| `items.search_items` | No | Already existed |
| `availability.check_availability` | No | The agent-facing tool, not `get_matrix` |
| `quotes.create_quote_draft` | No | Already created real `Cortex Rental Transaction` docs |
| `quotes.preview_pricing` | **Yes** | Read-only twin of `create_draft_handler` — same `PricingService` calls, nothing persisted. Added because the design system explicitly forbids re-implementing the billable-days curve in JavaScript ("Le prix est présenté comme résultat du PricingService, pas comme calcul frontend") — there was no way to show a live price preview honestly without it. |

All of the pre-existing endpoints are gated by `require_agent_scope`,
which (per `permissions/agent_scopes.py`) already grants access to any
`HUMAN_STAFF_ROLES` member — so this page didn't need any new
permission plumbing, just a real caller.

One small pre-existing-endpoint fix bundled in: `create_quote_draft`'s
`lines` argument now gets `frappe.parse_json()`'d when it arrives as a
string (how a browser's `frappe.call()` form-encodes a nested array) —
previously only ever called with a real Python list (MCP, tests), so
this path was untested until this page needed it.

## What's real vs. disclosed simplification

| Behavior | Status |
|---|---|
| Customer search/create, item search, line pricing, availability check, quote creation | Real — every one of these hits the actual backend, same as the Availability grid |
| Live price preview as lines/dates change | Real, server-computed (`preview_pricing`), debounced 400ms |
| Per-line availability badge | Real (`check_availability`), debounced 500ms, batched into one call for all lines rather than one call per line |
| Serial number auto-assignment | **Not built — and not a gap.** A Quote never blocks inventory or claims specific Serial Nos; that only happens at Reservation confirmation (`TransactionStateService`). The original mockup showed serial assignment on the composer, but that's a Reservation-time concern, not a Quote-creation one — building it here would imply a guarantee this state doesn't make. |
| Customer-tier automatic discount | **Not built.** `PricingService` has no customer-tier discount logic today — `discount_percentage` is a manual per-line field, not auto-populated. |
| Readiness indicator (compte/assurance/paiement) during composition | **Not shown.** `create_draft_handler` always returns all three as `false` — nothing computes real readiness before a transaction exists. Shown honestly on the real transaction Form after creation instead of faked here. |
| Prefill from Availability's "+ Créer une soumission" | Real — `frappe.route_options` (the standard Frappe cross-page handoff, not a URL query string), read once on mount and cleared immediately. Only dates carry over; Availability's grid has no per-item selection state to also prefill. |
| Post-submit destination | Real navigation to the created transaction's native Frappe Form (`frappe.set_route`) — no custom confirmation screen. |

## Not done in this pass

Tracked in `HANDOFF.md`: accessory/kit suggestions, free-text lines,
per-line permission-gated discount overrides (the spec's "rabais ligne
contrôlé par permission" — this pass's discount field has no
permission check at all yet).
