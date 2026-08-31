# Cortex Operations System — component contracts

All components live in
`apps/cortex_rental/cortex_rental/public/js/cortex_shared/`. Plain Vue
3 `<script setup>` SFCs, no TypeScript (see `docs/design-system.md`
"Packaging") — prop shapes are documented here by hand instead of
inferred from `.d.ts` files.

## CortexStatusBadge

Renders a business state as icon + label + color — never color alone.

| Prop | Type | Required | Notes |
|---|---|---|---|
| `state` | `string` | yes | Key into `stateMeta.js`'s `STATE_META`. Unknown keys render with a `?` glyph and the raw key as the label rather than throwing — fails visibly, not silently. |
| `label` | `string` | no | Overrides the default French label. |
| `tooltip` | `string` | no | Overrides the default `title` attribute (defaults to the label). |

No events. Accessibility: glyph is `aria-hidden`, label text carries the
meaning for screen readers; `title` provides the tooltip.

## CortexRiskBadge

Same shape as `CortexStatusBadge` for `level: 'low' | 'medium' | 'high'`
(approval risk, per the Approvals mockup). Props: `level` (required),
`label` (optional override).

## CortexReadinessIndicator

Renders a checklist that explains *why* something is blocked, not just
red/green dots (explicit spec requirement).

| Prop | Type | Required | Notes |
|---|---|---|---|
| `title` | `string` | no | e.g. "Préparation contrat". |
| `items` | `Array<{key, label, ready, hint?}>` | yes | `hint` renders only when `ready` is false. |
| `blockedMessage` | `string` | no | Shown only when at least one item is not ready. |

## CortexEmptyState

| Prop | Type | Required |
|---|---|---|
| `message` | `string` | yes |
| `actionLabel` | `string` | no |

Emits `action` when the action button is clicked (no built-in
navigation — the caller decides). `#icon` slot for an optional visual.

## CortexPageHeader

Implements the "Page Header" grammar from `docs/design-system.md`
("Structure de chaque écran" §1): title + status, subtitle, secondary
actions left of the primary action.

| Prop | Type | Required |
|---|---|---|
| `title` | `string` | yes |
| `subtitle` | `string` | no |

Slots: `status` (next to the title, e.g. a `CortexStatusBadge`),
`secondary` (neutral buttons), `primary` (the one primary action).

## CortexEvidenceLink — placeholder

**Not wired to a real preview/download endpoint** — no such endpoint
exists yet (`services/evidence.py` only stores a reference today).
Renders chips from data the caller already has.

| Prop | Type | Required |
|---|---|---|
| `items` | `Array<{label, source?, date?, author?, hash?, confidence?}>` | yes |

`confidence` is one of `'high' \| 'medium' \| 'low'`, rendered as text
(not a color-only signal). Emits `open` with the clicked item — the
caller decides what "open" means until a real preview endpoint exists.

## CortexAuditTimeline — placeholder

**Does not fetch `Audit Event` records itself** — renders whatever the
caller passes in. Dual-mode per spec: operational sentence vs.
technical detail (request ID, actor ID, policy version, payload diff).

| Prop | Type | Required |
|---|---|---|
| `events` | `Array<{timestamp, actorLabel, text, technical?: {...}}>` | yes |

Internal state: a mode toggle (`operational`/`technical`), local to the
component.

## CortexLoadingState

Skeleton rows — never a fake zero/"available" value while loading (per
spec). Props: `rows` (default 4), `rowHeight` (default 32px). Rendered
with `role="status"` `aria-live="polite"` so screen readers announce
the loading state once, not per skeleton row.

## CortexErrorState

Forces the caller to state the consequence, not just the error, per
the spec's explicit example ("Aucune réservation n'a été créée").

| Prop | Type | Required | Notes |
|---|---|---|---|
| `message` | `string` | yes | What went wrong. |
| `consequence` | `string` | no | What did *not* happen as a result — strongly recommended, not runtime-enforced (plain Vue has no prop validators beyond type). |
| `retryLabel` | `string` | no | Defaults to "Réessayer". |

Emits `retry`. `role="alert"` so assistive tech announces it immediately.

## CortexKpiSummary

Full-width KPI card per `design-system-accounting-pnl.md` §11: Total
Income − Total Expense = Net Profit, on one shared baseline. Not
Accounting-specific by name — reusable by any future financial
statement screen needing the same three-figure summary.

| Prop | Type | Required |
|---|---|---|
| `totalIncome` | `number` | no (default `0`) |
| `totalExpense` | `number` | no (default `0`) |
| `netProfit` | `number` | no (default `0`) |
| `currency` | `string` | no (default `"USD"`) |
| `locale` | `string` | no (default `"en-US"`) |

Formats via `Intl.NumberFormat` (`formatters.js`'s `formatCurrency`),
never a manual string build. No events.

## CortexFinancialChart

Hand-rolled inline SVG line chart (no charting library — see
`cortex-tokens.css` "Packaging" for why this app avoids new
dependencies). Renders whatever accumulation state the caller's data is
already in — does not accumulate client-side.

| Prop | Type | Required |
|---|---|---|
| `periods` | `Array<{key, label, income, expense, profitLoss}>` | yes |
| `currency` | `string` | no (default `"USD"`) |
| `locale` | `string` | no (default `"en-US"`) |

Series colors come from `--accounting-income`/`--accounting-expense`/
`--accounting-profit` (`cortex-tokens.css`), not the general Cortex
indigo brand tokens. Y-axis scale is computed from the real data's max
value, not a fixed mockup scale. Hover shows a tooltip naming each
series (never color alone); a visually-hidden (`cx-sr-only`) real
`<table>` of the same data ships alongside the SVG for screen readers,
per spec §12's accessibility requirement.

## CortexFinancialTable / CortexAccountRow

Hierarchical financial statement table (spec §13). Real
`<table>`/`<th scope="col">` markup — genuinely tabular data, unlike
the flex-div grid `CortexAvailability.vue` uses for its calendar.

**CortexFinancialTable**

| Prop | Type | Required |
|---|---|---|
| `periods` | `Array<{key, label}>` | yes |
| `accounts` | `Array<AccountRow>` | yes |
| `currency` | `string` | no (default `"USD"`) |
| `locale` | `string` | no (default `"en-US"`) |

**CortexAccountRow** (recursive — a component invoking itself by
filename in its own template, real Vue 3 SFC behavior). Root is a
`<tr>` plus a sibling `<template v-if>` of child `<tr>`s (Vue 3
multi-root/fragment components) — not verified against this app's real
`bench build` yet, same caveat as everything else with no bench in this
sandbox.

| Prop | Type | Required |
|---|---|---|
| `node` | `AccountRow` (`{id, name, depth, type, children, values, total}`) | yes |
| `periodKeys` | `Array<string>` | yes |
| `currency` | `string` | no |
| `locale` | `string` | no |

Local `expanded` state (default `true`), toggled by a 28px button with
`aria-expanded` and a `aria-label` naming the account — chevron rotates
90° per spec. Zero values render muted, negative values render in
danger red (never negative-signal by color alone — the minus sign in
the formatted currency string carries the meaning too).

## Shared module: `formatters.js`

Not a component — `formatCurrency(value, currency, locale)`, a thin
`Intl.NumberFormat` wrapper per spec §11. Used by every financial
component above instead of each one building its own currency string.

## Shared module: `stateMeta.js`

Not a component — the single source of truth every badge component
reads from, so two screens can't invent two different labels/icons for
the same state. Exports `STATE_META`, `RISK_META`,
`RENTAL_STATE_KEY`/`SERIAL_STATUS_KEY` (real DocType value → token key
mapping) and two lookup helpers. See `docs/design-system.md` "États —
wired vs. reserved" for which keys correspond to a real DocType value
today.
