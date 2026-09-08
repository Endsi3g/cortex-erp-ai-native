# Project: Cortex ERP AI-Native UI/UX Implementation

## Architecture
- **Framework & Frontend Core**: Vue 3 (`<script setup lang="ts">`), TypeScript Strict, Vite, Tailwind CSS, Pinia, Vue Router, Vue I18n (`fr-CA`, `en-CA`).
- **Location**: `apps/cortex_rental/cortex_rental/public/frontend`
- **Design System**: "Cortex OS — Operational Green" (Ink 900 `#08120D`, Ink 800 `#102019`, Ink 50 `#F2F7F4`, Green 500 `#087A43`, Green 400 `#14B86A`, Amber, Red, Violet, Blue).
- **Typography**: `Inter` for operational UI, `JetBrains Mono` for IDs, serials, hashes, and technical values.
- **Client Architecture**: Strictly typed `CortexApiClient` adapter interface isolating all frontend mutations from raw backend APIs, with isolated mock layer in `src/api/mock/`.
- **Privacy & Security**: Absolute tenant isolation and `OwnerStatementSafe` guarantee (zero renter PII in consignment views/exports/caches).
- **AI Operational Hierarchy**: `Voir l’état → comprendre le risque → vérifier les preuves → préparer une action → valider humainement → exécuter via le backend → enregistrer dans l’audit`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Design System & Tokens | "Cortex OS — Operational Green" tokens, typography (Inter/JetBrains Mono), accessible contrast (WCAG 2.2 AA), reduced-motion support | M1 (Gate 1) | R1 |
| F02 | App Shell & Universal Navigation | Topbar 56px, ⌘K search, ⌘J Copilot toggle, multi-tenant company selector, 248px/72px collapsible sidebar, 64px mobile bottom nav | M1 (Gate 1) | R1 |
| F03 | 7 Canonical AI States System | Reusable visual badges/cards with triple encoding (color, SVG icon, label fr-CA/en-CA), 1-click proof, source attribution | M1 (Gate 1) | R0, R4 |
| F04 | Typed API Client & Mock Layer | 32-method `CortexApiClient` interface, `MutationResponse` envelope, `DEMO-` prefixed fixture engine, data provenance | M1 (Gate 1) | R8 |
| F05 | Operations Overview (Screen 1) | Daily cockpit, 4 clickable KPI filter cards, departures/returns timeline, attention required widget, incoming & AI summary | M2 (Gate 2) | R2 |
| F06 | Availability Matrix (Screen 2) | Real-time matrix, Day (08:00/12:00/16:00/20:00)/Week/Month, sticky 288px equipment column, virtualized >100 rows, 2px red conflict border | M2 (Gate 2) | R2 |
| F07 | Rentals List (Screen 3) | Comprehensive rental directory with status filters, date range, search, persistent columns, individual actions | M2 (Gate 2) | R2 |
| F08 | Transaction Composer (Screen 4) | 3-step wizard (Client & dates, Items & prices, Review & create), 7d=3d pricing rule, 400ms availability check, auto-assign serials | M2 (Gate 2) | R2 |
| F09 | Rental Transaction Detail (Screen 5) | 360° view with 6 tabs (Overview with Readiness indicator, Equipment & Serials, Docs & Evidence, Check-in, Finance & P&L, Audit Log) | M2 (Gate 2) | R2 |
| F10 | Warehouse Check-out Scanner (Screen 6) | High-speed checkout mode with 52px persistent autofocus input, >=44px touch targets, visual/sound/haptic feedback, duplicate/unknown handling | M2 (Gate 2) | R3 |
| F11 | Warehouse Check-in Scanner (Screen 7) | Item-by-item return, partial returns handling, 1-click anomaly logging (missing, damage photo upload, quarantine), return diff summary | M2 (Gate 2) | R3 |
| F12 | Approval Queue SAS (Screen 8) | Human validation gate, before/after diff comparison, direct evidence link, instant revalidation, idempotency protection, no self-approval | M2 (Gate 2) | R4 |
| F13 | Consignment Dashboard (Screen 14) | Third-party owner directory, gross revenue, payout calculation, status summary | M2 (Gate 2) | R5 |
| F14 | Owner Statement & Isolation (Screen 15) | `OwnerStatementSafe` strictly sanitized view/export, permanent privacy banner, zero renter PII (8 privacy tests) | M2 (Gate 2) | R5, R10 |
| F15 | Copilot Contextual Sidebar (Screen 19) | 416px slide-out drawer (⌘J), 14 state transitions, contextually bound to active entity, 1-click proof, human validation CTA | M2 (Gate 2) | R4, R13 |
| F16 | Incoming Requests & Extraction (Screen 16) | Structured intake of email/PDF requests by AI Intake Agent, confidence scores, missing field indicators, 1-click Composer conversion | M3 (Gate 3) | R4 |
| F17 | AI Drafts Centralization (Screen 17) | Unapproved AI proposals dashboard: edit, open in flow, submit to approval, reject with reason, archive | M3 (Gate 3) | R4 |
| F18 | Agent Activity & Telemetry (Screen 18) | Admin dashboard for agent execution telemetry: tools invoked, latency, LLM model (Gemini/Sonnet), token costs, trace timeline | M3 (Gate 3) | R4 |
| F19 | Equipment List (Screen 9) | Catalog of serialized and quantity-based rentable equipment with filters and availability previews | M4 (Gate 4) | R5 |
| F20 | Equipment Detail (Screen 10) | Comprehensive equipment sheet, rental profile, required/optional accessories, mini availability timeline | M4 (Gate 4) | R5 |
| F21 | Serial Number Detail (Screen 11) | Unit tracking, ownership status, consignment payout rate, append-only maintenance history | M4 (Gate 4) | R5 |
| F22 | Owners Directory (Screen 13) | Third-party consignment owner directory, contact information, payout terms | M4 (Gate 4) | R5 |
| F23 | Append-Only Audit Log (Screen 24) | Immutable operational journal with human readable summary and technical JSON diff switcher (request_id, actor, policy_version, proof hash) | M4 (Gate 4) | R5 |
| F24 | Import & Migration Wizard (Screen 23) | 6-step legacy data import wizard (quarantine, field mapping, diff preview, validation, import execution, rollback) | M4 (Gate 4) | R5 |
| F25 | Kits & Packages Composition (Screen 12) | Package bundling without physical inventory duplication, optional component overrides | M5 (Gate 5) | R5 |
| F26 | Full Assistant Page (Screen 20) | Full-screen multi-turn conversational interface with entity pinning, evidence explorer, and audit traceability | M5 (Gate 5) | R4 |
| F27 | Rental Policies Browser (Screen 21) | Read-only viewer for versioned pricing curves, availability rules, and multi-tenant rental policies | M5 (Gate 5) | R5 |
| F28 | Team & Roles Permissions Matrix (Screen 22) | Role-based permission matrix viewer and service account identification | M5 (Gate 5) | R5 |
| F29 | Transversal Flows 1 to 5 (E2E Demo-Ready) | Flow 1 (Email→Reservation), Flow 2 (Matrix→Quote), Flow 3 (Contract→Check-in), Flow 4 (Consignment→Statement), Flow 5 (Copilot→Approval) | M5 (Gate 5) | R6 |
| F30 | Handoff & Quality Assurance | Complete Vitest test suite, a11y & contrast verification, responsive checklist (1440/1280/768/390), final `HANDOFF-UI.md` | M5 (Gate 5) | R14, R15 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Preflight & Codebase Survey | Preflight exploration, contract mapping, drafting 5 preflight docs | none | DONE |
| M1 | Gate 1 — Foundation | Scaffolding, TypeScript config, "Cortex OS" Design Tokens, Base Components, 7 AI States, App Shell & Router (24 routes), CortexApiClient & Mock Layer, i18n fr-CA/en-CA | M0 | DONE |
| M2 | Gate 2 — P0 Demo-Critical | Operations Overview (1), Availability Matrix (2), Rentals List (3), Composer (4), Rental Detail (5), Check-out (6), Check-in (7), Approval Queue (8), Consignment Dashboard (14), Owner Statement (15), Copilot (19) | M1 | IN_PROGRESS |
| M3 | Gate 3 — P1 Intake & Intelligence | Incoming Requests (16), AI Drafts (17), Agent Activity (18), 7 AI States shared integration, Flow 1 E2E simulation | M2 | PLANNED |
| M4 | Gate 4 — P1 Catalog, Audit & Migration | Equipment List (9), Equipment Detail (10), Serial Detail (11), Owners (13), Audit Log (24), Import Wizard (23) | M3 | PLANNED |
| M5 | Gate 5 — P2 Polish & Final Deliverables | Full Assistant (20), Kits (12), Policies (21), Team (22), Test Suite (Unit/Component/Privacy/A11y/Responsive), HANDOFF-UI.md | M4 | PLANNED |

## Code Layout
```
apps/cortex_rental/cortex_rental/public/frontend/
├── src/
│   ├── app/
│   │   ├── router/          # 24 canonical routes with metadata & guards
│   │   ├── layouts/         # AppLayout (desktop/tablet) & MobileLayout (390px)
│   │   ├── providers/       # Context & App providers
│   │   └── i18n/            # fr-CA and en-CA locales & formatters
│   ├── api/
│   │   ├── CortexApiClient.ts # Central typed client interface
│   │   ├── contracts/       # Request/Response types, Zod schemas, MutationResponse
│   │   ├── adapters/        # Concrete HTTP adapter for Frappe API
│   │   └── mock/            # MockCortexApiClient with DEMO- fixtures & latency
│   ├── design-system/
│   │   ├── tokens/          # Colors, typography, spacing, shadows, borders
│   │   ├── components/      # Base UI, 7 AI State badges/cards, 5 UI states
│   │   ├── icons/           # Feather/Lucide SVG icons
│   │   └── styles/          # Tailwind & custom CSS
│   ├── features/
│   │   ├── operations/      # Screen 1 (Operations Overview)
│   │   ├── availability/    # Screen 2 (Availability Matrix)
│   │   ├── rentals/         # Screens 3, 4, 5 (List, Composer, Detail)
│   │   ├── checkout/        # Screen 6 (Check-out Scanner)
│   │   ├── checkin/         # Screen 7 (Check-in Scanner & Anomalies)
│   │   ├── approvals/       # Screen 8 (Approval Queue SAS)
│   │   ├── catalog/         # Screens 9, 10, 11, 12 (Equipment, Serials, Kits)
│   │   ├── consignment/     # Screens 13, 14, 15 (Owners, Dashboard, Statement)
│   │   ├── intelligence/    # Screens 16, 17, 18 (Incoming, Drafts, Activity)
│   │   ├── administration/  # Screens 21, 22, 23, 24 (Policies, Team, Import, Audit)
│   │   └── copilot/         # Screens 19, 20 (Sidebar Drawer & Full Assistant)
│   ├── composables/         # Reusable Vue 3 logic (useTenant, useScanner, etc.)
│   ├── stores/              # Pinia stores (session, navigation, copilot, approvals)
│   ├── types/               # Domain TypeScript types
│   ├── utils/               # Formatters (currency CAD, localized dates, diff)
│   └── test/                # Test utilities, privacy assertions, a11y tests
├── package.json
├── vite.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

## Ownership Matrix
| Zone of Code | Exclusive Owner Role | Subagent Specialization |
|---|---|---|
| `src/design-system/**`, `src/styles/**` | Design System Lead | `teamwork_preview_worker` (Design System) |
| `src/app/**`, `src/layouts/**`, `src/router/**` | App Shell & Navigation Engineer | `teamwork_preview_worker` (App Shell) |
| `features/operations/**`, `features/availability/**`, `features/rentals/**` | Operations UI Engineer | `teamwork_preview_worker` (Operations UI) |
| `features/checkout/**`, `features/checkin/**` | Warehouse UI Engineer | `teamwork_preview_worker` (Warehouse UI) |
| `features/consignment/**`, `features/finance/**` | Finance & Consignment UI Engineer | `teamwork_preview_worker` (Finance UI) |
| `features/intelligence/**`, `features/copilot/**` | Intelligence UI Engineer | `teamwork_preview_worker` (Intelligence UI) |
| `src/api/**`, `src/types/**`, `src/i18n/**`, `src/test/**`, configs, docs | Platform & Quality Engineer | `teamwork_preview_worker` (Platform Lead) |
