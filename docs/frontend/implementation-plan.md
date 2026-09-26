# Cortex ERP AI-Native — Frontend Implementation Plan

## 1. Vision & Strategy
Cortex is an AI-native operational cockpit and cloud ERP for audiovisual, cinema, broadcast, and live event equipment rental companies.
- **Core Product Promise**: "Run every rental with complete control."
- **AI Operational Hierarchy**: `Voir l'état → comprendre le risque → vérifier les preuves → préparer une action → valider humainement → exécuter via le backend → enregistrer dans l'audit`.

## 2. Phased Delivery Roadmap & Quality Gates

### Gate 1 — Foundation & Scaffolding (Milestone 1)
- **Scope**:
  - Frontend repository setup in `apps/cortex_rental/frontend`
  - TypeScript strict configuration, Vite, Tailwind CSS, Pinia, Vue Router, Vue I18n
  - Design Tokens "Cortex OS — Operational Green" (`#08120D`, `#087A43`, `#14B86A`)
  - Reusable base components (`CortexButton`, `CortexInput`, `CortexModal`, `CortexTable`, etc.)
  - 7 Canonical AI state badges and structured cards
  - 5 Standard UI state handlers (Skeleton, Empty, Error, Stale, Permission Denied)
  - `CortexApiClient` 32-method interface with `MutationResponse` envelope
  - Hermetically isolated `MockCortexApiClient` with `DEMO-` synthetic datasets
  - Test harness with Vitest, `@vue/test-utils`, `happy-dom`, and contrast verification
- **Exit Criteria**:
  - `npm run build` and `npm run typecheck` succeed with zero errors and zero `any`.
  - All 24 routes resolve in Vue Router without broken layout or unhandled exceptions.
  - Token contrast validates against WCAG 2.2 AA.

### Gate 2 — P0 Demo-Critical Features (Milestone 2)
- **Scope**:
  - Screen 1: Operations Overview (`/app/cortex-operations`) with 4 KPI cards & daily timeline.
  - Screen 2: Availability Matrix (`/app/cortex-availability`) with virtualized grid, sticky equipment column, 2px red conflict border, and Day/Week/Month views.
  - Screen 3: Rentals List (`/app/cortex-rentals`) with status filters and search.
  - Screen 4: Transaction Composer (`/app/cortex-rental/new`) 3-step wizard with 7d=3d rule.
  - Screen 5: Rental Transaction Detail (`/app/cortex-rental/:name`) 360° view with 6 tabs.
  - Screen 6: Check-out Scanner (`/app/cortex-checkout/:rental`) with 52px rapid autofocus.
  - Screen 7: Check-in Scanner (`/app/cortex-checkin/:rental`) with partial returns & 1-click anomaly logging.
  - Screen 8: Approval Queue SAS (`/app/cortex-approvals`) with before/after diff & evidence viewer.
  - Screen 14: Consignment Dashboard (`/app/cortex-consignment`) with owner payout summaries.
  - Screen 15: Owner Statement (`/app/cortex-owner-statement/:owner/:period`) with `OwnerStatementSafe` guarantee.
  - Screen 19: Copilot Sidebar (416px, ⌘J) with 14 state transitions.
- **Exit Criteria**:
  - Transversal Flows 2, 3, 4, and 5 demo-ready on synthetic data.
  - 8 mandatory privacy tests pass on Owner Statement.

### Gate 3 — P1 Intake & Intelligence (Milestone 3)
- **Scope**:
  - Screen 16: Incoming Requests (`/app/cortex-incoming`) with confidence scores & missing field indicators.
  - Screen 17: AI Drafts (`/app/cortex-ai-drafts`) with unapproved proposal management.
  - Screen 18: Agent Activity (`/app/cortex-agent-activity`) with telemetry, model costs, and tool latency.
- **Exit Criteria**:
  - Flow 1 (Email Intake to Confirmed Reservation) demo-ready in simulation.

### Gate 4 — P1 Catalog, Audit & Migration (Milestone 4)
- **Scope**:
  - Screen 9: Equipment List (`/app/cortex-equipment`).
  - Screen 10: Equipment Detail (`/app/cortex-equipment/:item`).
  - Screen 11: Serial Number Detail (`/app/cortex-serial/:serial`).
  - Screen 13: Consignment Owners (`/app/cortex-consignment-owner`).
  - Screen 23: Import & Migration Wizard (`/app/cortex-import`) 6-step pipeline.
  - Screen 24: Immutable Audit Log (`/app/cortex-audit-event`) with dual JSON diff switcher.
- **Exit Criteria**:
  - Seamless navigation between P0 transactions and P1 master data entities.

### Gate 5 — P2 & Final Quality Polish (Milestone 5)
- **Scope**:
  - Screen 12: Kits & Accessories (`/app/cortex-kits`).
  - Screen 20: Full Assistant Page (`/app/cortex-assistant`).
  - Screen 21: Rental Policies (`/app/cortex-rental-policy`).
  - Screen 22: Team & Roles (`/app/cortex-team`).
  - Full automated test suite (Unit, Component, Privacy, A11y, Responsive).
  - Final `HANDOFF-UI.md` documentation.
- **Exit Criteria**:
  - 100% route coverage across all 24 screens.
  - Responsive verification across 1440px, 1280px, 768px, and 390px.
