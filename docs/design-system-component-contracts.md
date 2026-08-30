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

## Shared module: `stateMeta.js`

Not a component — the single source of truth every badge component
reads from, so two screens can't invent two different labels/icons for
the same state. Exports `STATE_META`, `RISK_META`,
`RENTAL_STATE_KEY`/`SERIAL_STATUS_KEY` (real DocType value → token key
mapping) and two lookup helpers. See `docs/design-system.md` "États —
wired vs. reserved" for which keys correspond to a real DocType value
today.
