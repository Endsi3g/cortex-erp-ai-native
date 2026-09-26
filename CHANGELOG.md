# Changelog — Cortex Security & Correctness Remediation

## v0.7.0-dev — AI-first Cortex (`feat/ai-home`)

### Phase A — One assistant engine, provider per company

- **Engine** (`services/ai/`): Anthropic Messages API called directly from Frappe, with streaming and tool use. Plain HTTP; the key lives only in `site_config` (`anthropic_api_key`). Provider and model are chosen per company in Cortex Company Settings: **Anthropic** (default, `claude-sonnet-5`) or **Onyx** (existing path). The choice is editable in Admin › Politiques.
- **Tools = the existing endpoints, run as the signed-in person**: customers, equipment, availability, server pricing, rentals, day overview, P&L, invoices, rental billing, consignment, AI inbox, policies, page links. The endpoints' own role and company checks apply; finance tools are not even offered to non-finance roles.
- **Writes are only proposed.** Quote, reservation, advance, final invoice, cancellation, serial status, new customer and inbound rejection each record a `Cortex AI Action` (new DocType) and return an `action_proposal` block. Nothing runs until a person confirms (confirmation lands in phase D).
- **Streaming**: text, tool progress and blocks are pushed on the `cortex_ai` Frappe realtime channel. The ⌘J panel shows them live and falls back to the full HTTP reply when the socket is unavailable.
- Every turn is recorded as a `Cortex Agent Run` with its tool calls, so it shows in Activité des agents.
- New block types: `widget` (read-tool data for the UI), `action_proposal`, `page_link`.
- Onyx is no longer required for the chat history endpoints (the Onyx client is created lazily, only when a company uses Onyx).

### Phase B — Claude-style home and conversation

- `/cortex` now opens on the conversation (route `home`). People without assistant access land on Operations, and `/assistant` redirects to the home page. The navigation rail and every regular page stay available.
- Claude look, scoped to AI surfaces (`.claude-surface`: ivory background, serif greeting and answers, beige user bubbles, clay accent). Tables, forms and reports keep the ERPNext style.
- **Home**: time-of-day greeting, large rounded composer (Enter to send, Shift+Enter for a new line), suggestions filtered by the person's permissions, and a collapsible history grouped by today, last 7 days and older (`?c=<session>` reopens one). The composer docks at the bottom once the conversation starts, with a live streaming caret and a copy button on answers.
- The ⌘J panel uses the same conversation components, with the current page as context. It is hidden on the home page.
- Model text is rendered as Markdown and sanitized (DOMPurify; no scripts, images, forms or `javascript:` links). Internal links open inside the app.

## v0.6.0-dev — 2026-09-25 — Refonte UI complète (`feat/ui-rebuild`, lots 1 à 8)

Not verified on a live bench: see HANDOFF §0 for the deployment and per-screen checks on the tower.

### Lot 1 — Foundations, shell and Compte de résultat

**Application**
- The Cortex UI is now a single Vue 3 + Frappe UI app served by Frappe under `/cortex/*` (`www/cortex.py`, `website_route_rules`). Sources moved from `cortex_rental/public/frontend` (which Frappe exposed publicly under `/assets`, source and `node_modules` included) to `apps/cortex_rental/frontend`; only the build lands in `public/frontend`.
- Removed the legacy Desk pages (`page/cortex_*`), their bundles (`public/js/*`), the Desk CSS injection and the global Desk copilot launcher. The Desk workspace is now a plain entry point (link to `/cortex` + real DocType lists).
- ERPNext Desk is standard again: removed `setup_cortex_sidebar` (it hid every non-Cortex workspace in the database on every login) and the sidebar override; patch `v1_0.restore_erpnext_workspaces` makes public workspaces visible again.

**Security**
- Tenant resolution no longer falls back to the hard-coded "CineRental Montreal" nor to the user-editable session default Company. Access comes from User Permission (or System Manager); a single-Company site grants that Company; otherwise nothing.
- Roles referenced by DocType permissions (`Rental Manager`, `Rental Operator`, `Pricing Manager`, `Auditor`) are now shipped as fixtures.

**Shell (pixel-matched to `inspiration/image.png`)**
- 50px rail, 48px top bar, 46px page header, 28px Frappe UI controls, espresso palette. Measured deviations ≤ 1.5px (automated comparison through the dev-only `frontend/preview/`).
- Navigation built from the route table and filtered by server permissions; ⌘K search backed by the new `api/v1/search.global_search` (tenant-scoped); removed hard-coded DEMO links, fake search results, the invented "3" inbox badge and the default pending-approvals count of 4.

**Finance**
- Compte de résultat (`/cortex/finance/profit-and-loss`): ERPNext filter bar (company, finance book, fiscal years or date range, periodicity, currency, cost center, accounting dimensions, project, report view, accumulated values, default FB entries), KPI summary, chart, tree table with row filters, General Ledger drill-down, CSV export with formula-injection guard, print.
- `get_profit_and_loss` now recognises ERPNext v14/v15 labels (`'Total Income (Credit)'`, `'Profit for the year'`, spacer rows) and returns `available: false` with a reason instead of a zeroed statement when the report fails. New `get_pnl_filter_options`.

### Lot 2 — Finance: advance + balance billing on ERPNext documents

- Reservation now creates and submits the ERPNext **Sales Order** with the server-priced period lines (billable days, discounts) and the company's sales tax template (TPS/TVQ). The previous sync created orders at the *daily* rate, lost the link after save and swallowed every error; ERPNext failures now fail the reservation with ERPNext's message.
- Requested **advance** = share of the order's grand total (new DocType **Cortex Company Settings**, 30% by default) + equipment guarantee (`deposit_required` × qty). Recorded as a native ERPNext **Payment Entry** against the order (submitted for accounting roles, draft otherwise); `payment_ready` follows the order's `advance_paid`.
- After return, a **draft balance Sales Invoice** is mapped from the order with advances allocated and damage / loss lines from completed check-ins; it refuses (instead of dropping charges) when the damage/loss items are not configured. A person submits it in ERPNext.
- Traceability custom field `cortex_rental_transaction` on Sales Order, Sales Invoice and Payment Entry.
- **Factures et paiements** screen (`/cortex/finance/invoices`) on the shared ERPNext-style `DataTable`.
- Fixed a date bug across the app: Frappe `YYYY-MM-DD` values were read as UTC and shown one day early in Québec.
- To check on the tower after `bench migrate`: create a Cortex Company Settings record (tax template, damage and loss items), confirm a reservation creates a submitted Sales Order with taxes, record an advance, then prepare a balance invoice after a return.

### Lot 3 — Operations: overview, availability, rentals, composer, rental record

- **Availability grid rewritten**: blocks were positioned by rental *state* with hard-coded offsets, not by their dates. They are now placed on their real period, with overlapping rentals in separate lanes, conflicts outlined in red and a "now" line.
- **Operations overview** on a new tenant-scoped endpoint (`api/v1/operations.get_operations_overview`): departures/returns of the day, overdue returns, exceptions, rentals starting within 48 h with missing requirements, out-of-service serials, pending approvals and inbound requests. Removed the hard-coded DEMO timeline, alerts and incoming widgets.
- **Rentals list** on `list_rental_summaries` (one query per page instead of ~6 per row).
- **Composer** rebuilt as a single ERPNext-style form (create and edit): server pricing and per-line availability, same-category alternatives when a line conflicts, tax estimate from the company's ERPNext template (the official amounts stay ERPNext's).
- **Rental record** rebuilt: next action driven by `available_actions` computed on the server, requirement verification with audited reason (bug: contracts were impossible from Cortex because nothing could set these flags), billing tab (advance, payments, balance invoice), equipment & serials, audit; cancel with mandatory reason (closes the ERPNext order) and close (requires the balance invoice to be submitted).
- Fixed: the rental controller recomputed taxes from `tax_rate = 0` on every save, which would have wiped ERPNext taxes after reservation; the customer search read a non-existent `custom_insurance_valid_until` column (new custom field `cortex_insurance_valid_until`).
- Frontend state types now mirror the server state machine (removed `Draft`, `Partially Returned`, `Invoiced`; added `Closed`, `Disputed`, `Quarantine`); currency is the company's, not a hard-coded CAD.

### Lot 4 — Warehouse: check-out and check-in

- Check-out and check-in rebuilt on the shared ERPNext layout with a 52px scan field (audio/visual feedback, focus kept between scans) and a rental picker when no rental is given (replaces the DEMO links of the old menu).
- Check-in: per-unit condition and disposition, damage severity/type/repair cost, photo evidence uploaded as a private Frappe File attached to the rental (hashed and linked server-side), bulk quantities, and explicit finalisation (automatic, partial, settle with loss).
- Fixed: a unit returned with quantity 0 was recorded as 1 returned (`float(0 or 1.0)`), so lost equipment was never billed; the frontend offered check-in conditions the DocType rejects (`Missing_Accessory`, `Needs_Clean`); the check-in response was typed as a mutation envelope it never was.

### Lot 5 — Catalog: equipment, serial numbers, kits

- New `api/v1/catalog.py` (the old client called non-existent REST routes): equipment list with real fleet status, equipment record (ERPNext Item + rental profile + serials + pricing curve from the real PricingService), audited profile edits (catalog managers), serial record with rental / return / status history, status changes (quarantine, repair, release, missing, write-off) with mandatory reason.
- Kits are a Cortex model (**Cortex Rental Kit**, per company): required/optional components and a kit discount. Added to a rental they expand into real lines, each priced, availability-checked and reserved; the kit discount is accepted without the manager role only when it matches an active kit containing the item (kit reference stored on the line).
- Fixed two double-booking paths: confirmation re-checked availability line by line (two lines of the same item could exceed the fleet), and serial allocation could give the same serial to two lines of one rental. Staff availability checks now sum quantities per item too.

### Lot 6 — Customers 360 and consignment

- **Customers** (`api/v1/clients.py`): list with rentals, active rentals, outstanding balance and insurance status; 360° record with rentals, ERPNext invoices and payments; creation of an ERPNext Customer bound to the company; audited insurance verification (feeds the contract requirement).
- **Consignment computed from real rentals**: a serial is linked to its owner (`Serial No.cortex_consignment_owner`); statements take each owned unit's net revenue on rentals returned/closed in the month, at the owner's share. Workflow prepared (consignment manager) → approved → paid with ERPNext payment reference (finance). Agent tool `prepare_owner_statement` now takes owner + period only (it used to accept caller-supplied amounts and a default serial "SN-GENERIC-001").
- Owner statements keep the strict `OwnerStatementSafe` contract end to end; the screen refuses to render a statement carrying any field outside it.
- **Blocking fix**: `Consignment Payout` had a field named `owner`, a Frappe reserved fieldname — the DocType could not be migrated. Renamed to `consignment_owner`; a new schema test rejects reserved fieldnames, duplicate fields, dangling child tables and missing controllers across all DocTypes.
- Removed the fictitious server-side statement export (CSV is generated client-side with the injection guard; PDF through print).

### Lot 7 — AI: inbox, workspace, assistant, agent activity

- **AI inbox** (`api/v1/ai.py`): one list for pending approvals, inbound requests (with their latest extraction) and quote drafts created by agents, scoped to the active company. States are computed on the server (ready, needs review, low confidence below 0.7, extraction error, processing, then approved / applied / rejected).
- **AI workspace**: the source on the left (message and evidence, the approval's current vs proposed values, or the draft's lines), the AI's work on the right. Every decision button says exactly what it will record. "Prepare rental" opens the composer prefilled with the recognised dates and items, and saving links the request (`cortex.inbound.converted`). Rejections require a reason (`cortex.inbound.rejected`). Approving runs the approved transition under the approver's name, and people cannot approve their own requests.
- The model score is shown as reported by the agent, always labelled "not calibrated".
- **Assistant** (⌘J drawer and `/assistant` with history) now uses the real `api/v1/chat.py` gateway. The server picks the agent from the page key, and the active document is sent only as context the server re-checks. The server's typed blocks are rendered with facts, extracted values and model text visually distinct. The old store invented replies (a fixed "no conflict detected", confidence 0.96, a DEMO evidence id) and a draft count of 2; all of that is removed. When the assistant is not configured (`get_assistant_status`), the drawer says so instead of answering.
- **Agent activity** (`list_agent_activity`): agent runs with their tool calls (scope, status, duration, error), filters and CSV export; restricted to telemetry roles.
- **Blocking fixes, agent tools**:
  - `submit_approval_request` wrote to fields that do not exist on Approval Request, so no agent approval could be created. It now uses `requested_by_type/id`, `evidence_ids` and a new `rationale` field.
  - `create_quote_draft` / `preview_pricing` trusted the caller's `unit_rate`. Rates now come only from the company's rental profiles, and agents cannot apply discounts.
- Removed the REST calls to routes that never existed (`/intelligence/*`, `/copilot/*`) and their fixtures/types.

### Lot 8 — Administration: policies, team & roles, import & migration, audit log

- **Rental policies** (`api/v1/admin.py`): the effective billable-days curve for 1–31 days, showing which points come from a company rule and which from the standard grid. Rules (Rental Pricing Rule) are edited per duration, with billable days bounded to at most the calendar days. The company billing settings (advance %, equipment guarantee, tax template, damage/loss items) are editable too. Every change is audited with before and after values.
- **Team & roles**: System Manager only. Only human Cortex roles are granted or removed here; other roles a user holds are shown but never touched.
  - Agent roles and System Manager are never assignable here.
  - Nobody can edit their own roles.
  - Agent accounts are listed read-only.
  - Each change is audited (`cortex.team.roles_changed`).
- **Import & migration** (`api/v1/imports.py`, new DocTypes `Cortex Import Batch` / `Cortex Import Batch Record`): a 6-step CSV import of customers, equipment (ERPNext Item plus rental profile) or serial numbers (with consignment owner).
  - Steps: type → file → column mapping (French headers suggested) → row-by-row validation against the file and the site (duplicates, existing records, unknown catalog items or owners) → import → result.
  - Each row is created inside its own savepoint, and every created document is recorded on the batch.
  - Rollback deletes those documents newest first. A document that something else now links to is kept and reported. Import and rollback are audited.
  - Parsing and validation live in `services/importer.py`, which has no Frappe dependency and is fully unit-tested.
- **Audit log**: an append-only view of `Audit Event` with filters (action, document, actor, actor type, dates), a before/after/evidence/policy detail view and CSV export (up to 5,000 rows).
- Removed the REST calls to routes that never existed (`/policies`, `/team/roles`, `/migration/batches`, `/audit/events`) and the invented team data (role counts, masked API key).

**Quality (lot 1)**
- `tests/fake_frappe.py`: runs the `if frappe:` paths in pytest and validates every insert against the DocType JSON (unknown / missing mandatory fields).
- CI now typechecks, tests and builds the frontend.
- Not verified on a live bench in this lot; see HANDOFF for what to check on the tower.

## v0.5.0 — 2026-09-23

This release establishes the ERPNext-first, AI-native Cortex workspace and documents the implementation contract for future product and AI agents in `docs/frontend/CORTEX_UI_HANDOFF_V2.md`.

- Adds the Cortex AI Inbox, Workspace, and Audit views, with human review boundaries and server-owned decision rules.
- Connects rental composition, availability, approvals, check-in/check-out, and evidence workflows to Frappe domain APIs; pricing and inventory decisions remain server-side.
- Adds the Onyx/Ollama chat gateway and local deployment guidance. The local Qwen3 8B setup is configured, while complete browser-to-model workflow and tool execution still require end-to-end validation.
- Fixes session initialization and router loading so concurrent session checks are shared and a stalled Frappe session request times out instead of leaving the app loading indefinitely.
- Fixes Vite dependency interop for Feather Icons and `debug` in the frontend development build.
- Updates the ERPNext-inspired shell and responsive operational screens. Pixel-perfect parity with the supplied reference has not yet been confirmed by screenshot review.

Release validation: frontend production build, targeted session/router/API tests, Python compilation, and local service checks passed. The full frontend suite had one dynamic-import timeout under load (250 tests passed); that isolated route-import test passes when run alone, so the complete suite is not represented as fully green.

Known limitations: contract/invoice workflows, outbound customer messaging, full document-ingestion lifecycle, team assignment, and accounting integrations need further API/permission validation. Onyx chat and tool execution require end-to-end verification. See the canonical handoff for current scope and evidence.

---

Scope of this pass: a Claude security/design review of the Gemini-generated
`cortex_rental` Frappe app, `cortex-mcp` FastMCP facade, and supporting
infra found several BLOCKER/HIGH-severity gaps against the Cortex PRD
(multi-tenant isolation, state-machine enforcement, idempotency, CI
integrity, availability correctness, and a few PostgreSQL/duplication
inconsistencies left over from the Frappe migration). This changelog
documents what was found, what was fixed, and what remains open.

No prior git history existed for this branch — the Gemini-authored
scaffold was committed as a `chore: import initial Frappe/ERPNext
scaffold (baseline)` commit first, and every fix below is a separate,
atomic commit on top of it so the diff for each phase is reviewable on
its own.

Repository: https://github.com/Endsi3g/cortex-erp-ai-native
Branch: `test/PRD-demo-scenario`

---

## Phase 1 — Multi-tenant Company isolation (`ec59bb6`)

**Problem.** `X-Company-ID` (and, on the MCP side, a `company` argument
on every single tool) was accepted as-is with no check that the caller
was actually authorized for that Company. Any authenticated agent or
user could read or write another tenant's data by supplying a different
value — including via an LLM tool call, which means a prompt injected
through an ingested document could redirect a request cross-tenant.
Separately, `permission_query_conditions` was wired in `hooks.py` for 4
DocTypes but the implementation was a no-op stub (`return ""`), so
row-level filtering silently did nothing.

**Fixed.**
- `get_company_context()` now resolves the caller's authorized Companies
  server-side (Frappe `User Permission`) and only accepts a
  `X-Company-ID` hint that's already in that set.
- `require_agent_scope()` now checks the actual per-tool scope
  (`SCOPE_ROLE_MAP`) instead of "any Agent Service Account role".
- `permission_query_conditions` implemented for real, extended from 4 to
  9 Company-scoped DocTypes (was missing `Cortex Rental Transaction`,
  `Cortex Inbound Request`, `Consignment Owner`, `Rental Pricing Rule`,
  `Cortex Rental Item Profile` entirely).
- `Cortex Rental Item Profile` (the equipment catalog + rates actually
  used by `search_items`) had **no** `company` field at all — every
  tenant could see every other tenant's catalog and pricing. Added.
- Core ERPNext `Customer` isn't natively Company-scoped; added a
  `cortex_company` Custom Field (fixture) and filtered `search_customers`
  / `create_customer_draft` by it.
- Every MCP tool signature/schema no longer accepts `company` at all —
  the tenant is fixed to the MCP deployment's configured Company.
- Added Role fixtures for the PRD §5 role list (previously undefined
  anywhere in the codebase — `bench migrate` had nothing to provision).

## Phase 2 — Unconditional state-machine enforcement (`b1b5adc`)

**Problem.** `Cortex Rental Transaction.validate()` only recomputed
pricing. The actual transition rules (agent-cannot-self-advance,
Contract preconditions) lived exclusively in `transition_to()` — and
`Agent Service Account` held `write: 1` at the DocType level. A direct
`doc.save()` via the generic REST API or Desk UI could set
`rental_state` straight to `Contract` or `Closed`, bypassing every
check and the audit trail. Separately, `ApprovalRequest.approve()`
only executed a mutation for `entity_type == "Sales Order"`, which
nothing in this codebase creates — approving a request against the
actual `Cortex Rental Transaction` entity used everywhere else did
nothing.

**Fixed.**
- `validate()` now unconditionally diffs persisted vs. incoming
  `rental_state` and re-runs the state-machine check, regardless of
  entry path. New documents can only be created in `Quote`.
- `Agent Service Account`'s DocType permission on `Cortex Rental
  Transaction` reduced to read-only; writes only happen through the
  audited API layer.
- `ApprovalRequest.approve()` now dispatches to the real entity via
  `transition_to()`, re-validating preconditions as the human approver.

## Phase 3 — Idempotency-Key on every mutating endpoint (`a66e32d`)

**Problem.** No endpoint deduplicated writes. An agent retry after a
network timeout — a routine MCP failure mode — would create duplicate
quotes, approval requests, customer drafts, or consignment payouts.

**Fixed.** New `Cortex Idempotency Record` DocType + `with_idempotency()`
wrapper: replays the recorded response for a matching
(Company, scope, Idempotency-Key) retry, rejects key reuse with a
different payload, resolves concurrent-retry races via the DB's own
unique-name constraint. Wired into all 4 mutating endpoints.

## Phase 3.5 — Removed a live, unscoped, orphaned API surface (`0d9184b`)

**Problem, found while cleaning up.** A whole second, unversioned
`api/{quotes,approvals,items,availability}.py` module existed alongside
`api/v1/`, superseded but never deleted — and still `@frappe.whitelist`
live. It had **no** `require_agent_scope()` call at all, read
`X-Company-ID` with no authorization check (bypassing the Phase 1 fix
entirely, since it never called `get_company_context()`), and returned
fabricated fake data instead of real DocType writes. Confirmed
unreferenced by anything operational via repo-wide grep — deleted, with
the one stale doc reference (`docs/07`) updated with an explicit
"outdated, do not use" notice.

## Phase 4 — CI/security pipelines actually test the real code (`32f7442`)

**Problem.** `.github/workflows/ci.yml` and `security.yml` were still
the pre-migration Laravel/PHP pipeline (Pint, PHPStan, Pest, composer
audit, `apps/cortex-core`, `plugins/Webkul/CortexRental`) — none of
those paths exist in this repo. Every step was gated behind
`if [ -f ... ]`, so it printed a message and exited 0 regardless. CI was
structurally unable to fail.

**Fixed.** Rewrote both workflows for the real stack: `ruff check`,
`ruff format --check`, DocType JSON schema check, `pytest apps/` on
Python 3.11 (`ci.yml`), and `pip-audit` + secret-pattern scanning
(`security.yml`). Added root `ruff.toml`; discovered and fixed a config
gotcha where each app's own `pyproject.toml` (no `[tool.ruff]` section)
silently stopped Ruff's config auto-discovery, so both CI and
`bin/pre-claude-check.sh` now pass `--config ruff.toml` explicitly.
Applied `ruff format` once across `apps/` (61 files, formatting only) so
the newly-enforced format check starts green.

## Phase 5 — Availability correctness + mutation-time locking (`69a6d91`)

**Problem.** `AvailabilityService.check()` had two independent bugs:
`frappe.db.count(...) or 5.0` treated a real, correct zero-serial count
as falsy and fabricated "5 available"; every DB error was silently
swallowed into a fake "10 available". Quarantine/repair/missing units
were never excluded (`maintenance_qty` was a permanent stub). Separately,
ADR-002 explicitly deferred the mutation-time locking strategy
("Travaux Futurs / PRD-INV-003") — nothing prevented two concurrent
confirmations of the last unit from both succeeding.

**Fixed.** Both fabrication bugs removed; DB errors now propagate.
Added a `cortex_status` Custom Field on `Serial No`
(Active/Quarantine/Under Repair/Missing/Decommissioned — core ERPNext
has no such states) and excluded non-Active units from the fleet count.
Implemented the ADR-002 locking strategy: `transition_to()` into
Reservation/Contract now acquires a short-TTL Redis/Valkey lock per
(company, item_code) and re-checks availability under that lock before
committing.

Also removed a dangling `doc_events` block in `hooks.py` referencing
`cortex_rental.overrides.*` — no such module exists anywhere in the app,
so `bench migrate` would have failed on the import.

## Phase 6 — Dead duplicate code + infra drift cleanup (`8fbb106`)

- Deleted `cortex_rental/pricing.py`: a second, diverging implementation
  of the billable-days rule (disagreed with the canonical
  `services/pricing.py` for 2- and 4-day windows). Confirmed unreferenced
  after Phase 3.5.
- Unified the two independently-drifted PII denylists
  (`services/consignment.py` vs. `consignment_payout.py`) into one
  allowlist-first, denylist-backstop design, imported once.
- Fixed `"engine": "PostgreSQL"` → `"InnoDB"` on 6 DocType JSON files —
  the actual stack is MariaDB/InnoDB; an invalid engine value risked
  breaking `bench migrate`. Updated ADR-002 to match.

---

## Evidence

### Local, full validation (`./bin/pre-claude-check.sh`, final run)

```
[1/6] Git Status & Diff Summary...                     ✓ clean tree at HEAD
[2/6] git diff --check                                 ✓ no conflicts/whitespace issues
[3/6] Ruff (--config ruff.toml)                         ✓ All checks passed! · 63 files already formatted
[4/6] pytest apps/                                       23 passed, 8 skipped in 0.07s
[5/6] DocType JSON schema check                          ✓ 11/11 DocTypes validated
[6/6]                                                     ✓ TOUTES LES VÉRIFICATIONS SONT PASSÉES AVEC SUCCÈS
```

The 8 skipped tests are frappe-gated (`@unittest.skipUnless(frappe, ...)`)
— they exercise real multi-tenant isolation, quarantine exclusion, and
concurrent-reservation rejection against Frappe/MariaDB/Redis, none of
which are provisioned in this sandbox. They're written now so the first
real `bench --site <site> run-tests --app cortex_rental` on a live bench
proves the fixes, not just documents intent. See:
`apps/cortex_rental/cortex_rental/tests/test_multitenant_isolation.py`,
`test_availability_concurrency.py`.

### Live GitHub Actions run (not just local)

Pushed to `origin/test/PRD-demo-scenario` and the rewritten CI pipeline
ran for real:

```
$ gh run watch 33285056747 --exit-status
✓ test/PRD-demo-scenario Cortex CI Pipeline · 33285056747

JOBS
✓ Shell & Workflow Validation (pre-claude-check)  in 13s
✓ Python 3.11 — Ruff, DocType schema check & pytest  in 15s
```

Run: https://github.com/Endsi3g/cortex-erp-ai-native/actions/runs/33285056747

---

## Second wave — Gemini/Onyx validation, real bench attempt, and the 4 previously-flagged follow-ups

Requested as a follow-up to the section above. Status of each item that
was explicitly out of scope in the first wave:

### Gemini model test through the Onyx system prompt (`f6da28f`)

Onyx itself is not vendored in this repo (only its YAML config) and
could not be deployed here. What was actually run: the real
`cortex_intake_system.md` system prompt against the real
`gemini-3.7-flash` model (confirmed to exist via `GET /v1beta/models` —
the PRD/`.env.example`-specified model; `gemini-2.0-flash` is
deprecated, the API's own 404 pointed at `gemini-3.6-flash` first, but
3.7 is what's actually specified) on 4 of the 10
`prompt_injection_security_tests.json` cases. All 4 (system-prompt
override, cross-tenant exfiltration, indirect document injection,
forced availability hallucination) were correctly refused/contained.
See `docs/evals/2026-08-30-onyx-intake-gemini-3.7-flash.md` — this is a
prompt-quality signal, not a security proof; the code-level fixes hold
regardless of model behavior, and the full agentic tool-calling path
still needs a real Onyx+MCP+bench deployment.

### Real Frappe bench validation — attempted, blocked by environment, not code (`0aee7dc`)

Found and fixed a real bug while trying: `infra/docker/Dockerfile.bench`
referenced `frappe/bench:v15.0.0`, a tag that has **never existed** on
Docker Hub (verified against the actual tag list) — Gemini fabricated
it. Fixed to `frappe/bench:latest` (Framework v15 is chosen via `bench
init --frappe-branch version-15`, not the image tag), and swapped its
Postgres system deps for the real MariaDB ones. Provisioning itself hit
a hard wall: pulling MariaDB/Valkey filled this sandbox's disk to 99%
(146 MB free), and Docker Desktop crashed as a result. Cleaned up
(images/volumes removed, disk back to 6.2 GB free) rather than retrying
blind — 6.2 GB is still too tight for a full frappe+erpnext+node_modules
build, and this is a sandbox disk-space limit, not something fixable in
code. The frappe-gated tests throughout this repo remain unexecuted
here; they're written and ready for the first real `bench run-tests`.

### `Rental Item` vs. `Cortex Rental Item Profile` — decided (`0aee7dc`, ADR-004)

`Rental Item` deleted (confirmed unreferenced by any service/API/test).
`Cortex Rental Item Profile` is now the sole canonical catalog DocType;
gained the two fields `Rental Item` had that it genuinely needed
(`is_serialized`, `total_quantity`) so non-serialized items are now
modeled at all — `AvailabilityService` branches on `is_serialized`
instead of always counting `Serial No` rows. See
`docs/adr/ADR-004-rental-item-catalog-consolidation.md`.

### `Cortex Agent Run` / `Cortex Agent Tool Call` — implemented (`f6da28f`)

New DocTypes + a `@log_tool_call` decorator applied to all 7 agent-facing
endpoints, recording Success/Denied/Error with timing, correlated by a
caller-supplied `X-Request-ID` (cortex-mcp's `FrappeClient` now sends
one per call, plus `X-Cortex-Agent-Id` from a new `CORTEX_MCP_AGENT_ID`
setting) — separate from `Cortex Audit Event`, which only covers
business mutations, not the agent-facing API surface itself.

### Evidence/Extraction pipeline — implemented, explicitly bounded (`580c483`)

New `Cortex Evidence Reference` (hashed file/text, gated by a
`scanned_clean` flag) and `Cortex Extraction Run` (schema-validated,
confidence-scored) DocTypes. `intake_extraction_schema.json` — previously
pure documentation — is now actually enforced via `jsonschema`, with
`review_required` set below the 0.85 confidence threshold the intake
prompt already promises. **Not** implemented: the PRD's pre-signed
S3/MinIO "Upload Intent" direct-upload flow (no upload endpoint exists
anywhere in this codebase to build on — a separate infra feature) and
ClamAV scanning (the gate field exists; nothing sets it automatically
yet). Both are real gaps, not silently dropped.

### Check-in / partial-return / quarantine workflow — implemented (`5bfced0`)

New `Cortex Check-In` / `Cortex Check-In Item` DocTypes (human-staff-only,
no MCP tool — physical receiving needs a person scanning serial numbers).
Completing one updates each returned `Serial No`'s `cortex_status` per
disposition and a new `returned_qty` on the transaction line; the
transaction only moves `Checked Out -> Returned` once every line is
fully back, so a partial return correctly stays `Checked Out`.

### Still open after this wave

- **No live bench validation** (see above — environment-blocked, not
  a code gap).
- **`docs/07-frappe-erpnext-implementation-guide.md`** still documents
  a superseded design iteration; flagged inline, not rewritten.
- **1-site-per-client vs. shared-site-multi-Company** — Phase 1 makes
  the shared model safe, but the lower-risk pilot default
  recommendation from the original review still stands; not decided
  here.
- **Upload Intent (pre-signed S3/MinIO) + ClamAV scanning** — see
  Evidence/Extraction section above.

---

## Third wave — Onyx self-hosted decision, widget integration, README, release

### Onyx: self-hosted, widget-integrated, Gemini as default provider

Decision (2026-08-30): Onyx runs **self-hosted** (not Onyx Cloud), with
Gemini configured as its default LLM provider, and its chat surfaced
inside Cortex via the official `<onyx-chat-widget>` web component
rather than requiring a separate tab. Verified against the real Onyx
docs/GitHub repo before writing anything, following the same discipline
as the earlier `frappe/bench:v15.0.0` catch — no service names, image
tags, or config keys were guessed:

- `infra/onyx/README.md`: deployment via Onyx's own official installer/
  `docker-compose.yml` (`onyx-dot-app/onyx` — `relational_db`, `index`,
  `opensearch`, `cache`, `inference_model_server`, `minio`), explicitly
  **not** vendored into this repo's own compose file (a separate,
  independently-versioned stack, matching the PRD's "service
  indépendant" requirement as Onyx's own architecture, not just a
  Cortex preference). Documents the MCP-only connection path (Onyx never
  talks to Frappe/MariaDB directly) and that Gemini-as-default is
  configured through Onyx's own Admin Panel (Settings → LLM Providers)
  — no reliable env var name for this was found, so it's documented as
  a manual step rather than invented.
- `apps/cortex_rental/cortex_rental/www/onyx-assistant.{html,py}`: a
  Frappe `www` page (verified pattern: `.html` + `.py` with
  `get_context()`) embedding the widget, authenticated-users-only,
  reading `onyx_backend_url` / `onyx_widget_api_key` /
  `onyx_widget_script_url` from `site_config.json` (never committed).
  Explicitly documented as not weakening any server-side check — the
  widget is client-side UX; every real tool call still goes through
  Cortex MCP → the whitelisted, scope/tenant-checked API.
- **Known gap, not hidden**: the widget JS bundle's exact served path
  on a self-hosted deployment was not verified (public docs only show
  the cloud example `https://your-cdn.com/onyx-widget.js`) — the page
  defaults to `{backend_url}/widget/onyx-widget.js` but this needs
  confirming against a real deployment. `onyx_widget_api_key` must be a
  chat-only, limited-scope Onyx key (their docs are explicit it's
  visible in client-side page source).

### README, first release, PR fixes

- `README.md` updated to match the actual current DocType/service/
  endpoint inventory (was missing every DocType and service added in
  waves one and two), corrected two stale DocType names
  (`Cortex Consignment Owner`/`Cortex Approval Request` → their real
  names `Consignment Owner`/`Approval Request`), added the Onyx
  self-hosted + widget architecture, and links to `CHANGELOG.md`,
  `HANDOFF.md`, `infra/onyx/README.md`, and ADR-004.
- Fixed the failing `PR Conventions & PRD Compliance` check
  (`.github/workflows/pr-verification.yml`) on PR #1: it requires the
  PR description to reference a canonical PRD tag
  (`PRD-ARCH`/`PRD-NFR`/`PRD-TRX`/etc.), which the original description
  didn't include despite covering all of them.
- First tagged release: [v0.1.0](https://github.com/Endsi3g/cortex-erp-ai-native/releases/tag/v0.1.0)
  (notes mirror this changelog's summary).

---

## Fourth wave — README overclaim corrections (external review)

An external review of `README.md` (after v0.1.0) correctly flagged
several statements that were too strong for a codebase that has never
run against a live Frappe bench, plus a few real ambiguities. All
addressed directly in `README.md`, not just noted:

- Removed the "garantit zéro surréservation" claim — replaced with
  "conçu pour prévenir", matching what's actually been validated (unit
  tests in mock mode, no live concurrency test).
- The architecture diagram's "Authentification / Token + X-Company"
  block was genuinely ambiguous — could read as if the header
  authenticates. Split into separate Auth / Authz / Tenant-resolution
  lines matching what Phase 1 actually built.
- `Cortex Rental Transaction`'s `Closed` state clarified as operational,
  not financial — there is in fact no `erpnext_sales_invoice` link
  field yet, so this is a real, now-documented gap (added to
  `HANDOFF.md`'s open items), not just a wording fix.
- The Redis/Valkey lock description upgraded from "verrou atomique" to
  an accurate description of what it actually does: per-`item_code`
  (not per-`serial_no`) coordination + a re-check before write, with no
  MariaDB `SELECT ... FOR UPDATE` layered under it yet (ADR-002 already
  said this; the README didn't reflect it).
- `Audit Event`"append-only immuable" softened to "append-only
  applicatif" with the concrete gap named (`frappe.db.set_value()`,
  direct SQL, bench console, System Manager break-glass access aren't
  covered by the DocType hooks) — tracked as a new open item
  **PRD-ARCH-AUD-001** in `HANDOFF.md`.
- The Onyx widget integration marked "expérimental / à valider en
  staging" in both places it's mentioned, rather than implying it's a
  stable, verified integration.
- Added a "Statut de maturité" table (implemented vs. validated vs.
  proven-under-load, per domain) and a "before any pilot" checklist,
  both linking to `HANDOFF.md` rather than duplicating it.
- New `docs/compatibility-matrix.md`: the actual pinned vs. unpinned
  versions across the repo (Frappe/ERPNext are genuinely unpinned —
  `bench init --frappe-branch version-15` selects a branch, not a
  patch — and cortex-mcp's three Python version references
  (`pyproject.toml` `>=3.10`, Dockerfile `3.12-slim`, ruff `py311`)
  aren't aligned). Written from what the config files actually say, not
  guessed.

---

## Fifth wave — first real screen: Cortex Availability + Workspace

**Problem.** A first successful deploy against a real bench (screenshot
from a second machine) surfaced the actual gap this whole session had
been building toward but hadn't yet closed: no Frappe Workspace, no
custom page, nothing under `/app/cortex-*` — every backend fix so far
(DocTypes, services, whitelisted API methods) had no UI in front of it.
Opening the site showed the stock Frappe `Users` workspace and nothing
Cortex-specific to click. This wave builds the first real screen end to
end rather than adding more backend that stays invisible.

**Scope for this pass** (explicitly narrowed, confirmed with the user):
Workspace + the Availability matrix only — the first two items of the
five-screen priority order below. Composer/Check-in/Approvals/Assistant
are follow-ups, not attempted here.

**Frontend approach.** Verified against real, current sources before
writing anything (not guessed): the framework's own documented
["Using Vue in a Desk Page"](https://docs.frappe.io/framework/using-vue-inside-a-desk-page)
pattern — a native Frappe `Page` (`/app/cortex-availability`) whose
controller `frappe.require()`s a `.bundle.js` that Frappe's own
`bench build` compiles automatically, no separate npm/vite project, no
extra build step beyond what a Frappe bench already runs. This was
chosen over the `frappe-ui/vite` SPA plugin (also real, verified against
`frappe-ui`'s own `vite/README.md`) because that plugin serves a
top-level route (e.g. `/g`) outside the `/app/*` Desk namespace the PRD
explicitly wants these five screens under — it's the right tool for a
detached SPA (à la Helpdesk/CRM), not for a Desk-native page.
`frappe-ui`'s own component library is **not** imported yet: a real,
currently-open upstream issue documents esbuild breaking on
`frappe-ui` imports inside this exact Desk-page bundle pattern, and
there's no bench here to debug that against — the page is hand-built
with plain Vue 3 + scoped CSS instead, so it has zero new npm
dependencies to fail to install. Revisit `frappe-ui` for the next
screen once a real bench confirms the import issue does or doesn't
reproduce here.

**Added.**
- `cortex_rental/api/v1/availability.py`: `get_matrix` — a new
  human-staff-only (`require_human_staff_role`, no MCP tool, no agent
  scope) whitelisted method distinct from the existing agent-facing
  `check_availability`. Returns, per `Cortex Rental Item Profile`
  matching the Company/category/search filters, every transaction
  (`Quote`/`Reservation`/`Contract`/`Checked Out`) overlapping the
  requested window, plus a `has_conflict` flag. Company is always
  server-resolved via `get_company_context()` — never accepted from the
  client, same invariant as every other endpoint in this repo.
  Disclosed simplification: `has_conflict` sums blocking quantity across
  the *whole* requested window rather than sweeping day-by-day, so it
  can under-report a conflict confined to a sub-range — a visual aid
  only, not a booking-safety authority (that's still
  `AvailabilityService` at confirmation time, unchanged).
- `cortex_rental/cortex_rental/page/cortex_availability/`: the Page
  doctype record + controller, role-gated to the same
  `HUMAN_STAFF_ROLES` set as the backend (defense in depth, not the
  only gate).
- `cortex_rental/public/js/cortex_availability/`: `CortexAvailability.vue`
  + `cortex_availability.bundle.js`. Day/week/month toggle (month is a
  30-day rolling window, not a calendar-month grid — disclosed
  simplification, not built to avoid scope creep in this pass), category
  and state filters in a **collapsible sidebar with a real CSS width/
  opacity transition** (not the binary show/hide the user flagged as a
  bad interaction — this is scoped to Cortex's own pages only, per the
  user's explicit choice, not a change to Frappe Desk's native sidebar),
  search, per-item lane-stacked transaction blocks (blocks never
  overlap visually within a row even when multiple `Quote`s share a
  window), a conflict badge, and a color+icon+text badge for every state
  (never color alone, per the user's explicit requirement). Clicking a
  block navigates to the real `Cortex Rental Transaction` form
  (`frappe.set_route`); "Créer une soumission" opens a real
  `frappe.new_doc()` prefilled with the visible date range and the
  server-resolved Company — equipment lines still need to be added
  manually on the form (prefilling a child-table row from a route
  param is a real follow-up, not faked here).
- `cortex_rental/cortex_rental/workspace/cortex-rental/`: the `Cortex
  Rental` Workspace — shortcuts (Disponibilité, Transactions,
  Approbations, Assistant Onyx) and cards (Opérations, Catalogue,
  Clients, Finance, Intelligence, Administration) link **only** to
  DocTypes/pages that exist in this repo right now. Nothing points at a
  screen that hasn't been built yet — that's exactly the "text with
  dead links" complaint this wave exists to fix.
- Two new tests in `test_demo_scenario.py` covering `get_matrix_handler`
  (required-field validation, and the labeled-mock fallback when no
  live Frappe/DB is available — same contract as the existing
  `AvailabilityService` mock branch).

**Not done in this pass** (tracked in `HANDOFF.md`): Composer/Check-in/
Approvals/Assistant screens, `frappe-ui` component adoption, and any
verification against a live bench — this was written and syntax/unit-
tested here, but never opened in a browser, because no bench is
reachable from this environment. See `HANDOFF.md` §2 for the exact
build/reload commands to run on the machine that does have one.

---

## Sixth wave — Cortex Operations System design system foundation

**Problem.** A live screenshot from a real deployment (tower machine)
showed the app working but visually bare — no design system, no
reusable components, hand-copied colors per page (Availability's own
ad-hoc `STATE_META`). The user supplied a detailed, prescriptive design
spec ("Cortex Operations System": tokens, typography, spacing, 9
foundation components, WCAG 2.2 AA requirements) and asked for it to be
implemented — explicitly scoped to the foundation only, not the
remaining operational screens.

**Packaging decision** (confirmed with the user before writing code):
the spec's literal `apps/cortex_rental/frontend/` npm+Vite+TypeScript
project was **not** adopted. CSS custom properties + plain Vue SFCs
under `public/`, no new build pipeline — same reasoning as the fifth
wave's Desk-Page-over-SPA choice: a second, unverified build pipeline
with no bench to test it against would repeat a risk already avoided.
Tailwind (also specified) wasn't adopted for the same reason (needs a
PostCSS/Vite build step) — a small hand-rolled utility set instead.

**Added.**
- `apps/cortex_rental/cortex_rental/public/css/`: `cortex-tokens.css`
  (full palette + business-state tokens, spacing/radius/shadow/motion/
  focus-ring), `cortex-theme.css` (typography scale, focus-visible ring,
  `prefers-reduced-motion`, everything scoped under `.cortex-app` so
  nothing here can touch core Frappe Desk styling), `cortex-utilities.css`
  (buttons, badges, density modes, skeleton shimmer). Wired via
  `hooks.py`'s `app_include_css` (verified real hooks.py keys against
  docs.frappe.io before use — not guessed).
- `apps/cortex_rental/cortex_rental/public/js/cortex_shared/`: nine
  components (`CortexStatusBadge`, `CortexRiskBadge`,
  `CortexReadinessIndicator`, `CortexEmptyState`, `CortexPageHeader`,
  `CortexEvidenceLink`, `CortexAuditTimeline`, `CortexLoadingState`,
  `CortexErrorState`) plus `stateMeta.js`, the single source of truth
  every badge reads from (real `rental_state`/`cortex_status` values →
  design-token keys). `CortexEvidenceLink` and `CortexAuditTimeline` are
  explicitly placeholders — they render caller-supplied data, no real
  preview/download or Audit Event query wired yet.
- **États — wired vs. reserved** (`docs/design-system.md`): the spec
  proposes 16 state tokens; only 12 correspond to a real DocType value
  today (`Cortex Rental Transaction.rental_state` or
  `Serial No.cortex_status`). `draft`, `partial_return`,
  `invoice_prepared`, `invoiced` are defined as tokens (forward
  compatible) but explicitly marked as not reachable by any screen
  today — the same "no dead links" discipline as the Workspace, applied
  to design tokens.
- `bin/check-contrast.py`: a dependency-free WCAG 2.2 AA contrast
  checker (no JS test runner exists in this repo) that parses the
  actual shipped CSS tokens and computes real contrast ratios. **First
  run found every single state badge's border color from the spec
  failed the 3:1 non-text-contrast minimum against the page** — the
  pastel ~50-level border tints measured as low as 1.36:1, because the
  badge fills themselves are only ~1.1:1 against white, so the border
  is what actually has to carry the component's visible boundary, not
  decorate it. Fixed by swapping every state's border to its palette's
  500/600/700-level shade (same hue, same intent, real contrast) — not
  eyeballed, re-verified by the same script until it passed clean.
  Also caught and fixed two text-contrast shortfalls (`cancelled` label
  at 4.34:1, destructive-button hover text at 4.41:1, both under 4.5:1).
- Retrofitted `CortexAvailability.vue` (fifth wave) onto the new
  system: `CortexPageHeader` replaces its hand-rolled toolbar, calendar
  bars/legend/sidebar dots pull color and label from `stateMeta.js`
  instead of a locally duplicated map, loading/error/empty states use
  the new shared components, and every hardcoded hex color in its
  `<style>` block is now a `var(--cortex-*)` token reference. Confirms
  the design system actually works on a real screen rather than staying
  an unused foundation (deliberate choice, confirmed with the user).
- Branding: `app_logo_url`/`app_icon`/`app_color` in `hooks.py`
  (verified real hooks.py keys) plus a placeholder indigo monogram SVG
  — a real brand mark is a later decision, not invented here.
- `docs/design-system.md` and `docs/design-system-component-contracts.md`.

**Not done in this pass** (by design, per the spec's own scoping and
the user's confirmed choices): dark mode (light-mode tokens only —
the spec itself warns against a "faux dark mode" shipped unvalidated),
responsive breakpoints (no page needs tablette/mobile layout yet),
`frappe-ui` component adoption (same known esbuild-import risk as the
fifth wave), and the remaining page-specific components
(`CortexAvailabilityCell`, `CortexSerialAssignment`,
`CortexApprovalCard`, etc.) — those arrive with the screen that
actually uses them, not as unused scaffolding.

---

## Seventh wave — Cortex Chat Gateway backend (mocked, no live Onyx)

**Problem.** The user supplied two large specs: a Cortex↔Onyx chat
backend architecture and a Copilot UI panel. Explicitly scoped down
with the user before writing code (both specs are individually a
multi-day build) to backend first, mocked, no UI, as its own reviewable
PR — the panel is a separate follow-up PR once this contract exists.

**Security shape, enforced structurally, not just by convention.**
`SendMessageRequest`/`ChatContext` (`schemas/chat_schemas.py`, Pydantic
v2, `extra="forbid"`) have no field for `company`, `agent`, `model`, or
`allowed_tool_ids` at all — a client that tries to send one gets a hard
validation error, not a value that's silently ignored. Verified with a
throwaway script before writing any service code (sending each of those
four keys and confirming `ValidationError`), then locked in as tests
(`test_chat_gateway.py::TestClientCannotEscalate`).

**Added.**
- Three DocTypes: `Cortex Chat Session` (one per user/company/agent,
  `agent_profile` always server-resolved), `Cortex Chat Message`
  (human/agent/system turns, `content_sanitized` never a raw prompt),
  `Cortex Chat Context Snapshot` (the *resolved*, permission-checked
  context, not whatever the client originally sent). Chat privacy is a
  new permission dimension beyond Company scoping — two staff at the
  same Company must not read each other's conversations — added as
  `_own_chat_session_condition`/`_own_chat_child_condition` in
  `permissions/__init__.py` (Company filter AND `user =
  frappe.session.user`, bypassed only for System Manager).
- `services/agent_router.py`: `AgentRouter.resolve_agent(page)` — takes
  only a page, no client-requested-agent parameter exists to override
  it with (enforced by a test that inspects the function signature).
- `services/tool_policy.py`: `ToolPolicyResolver` — per-agent allowlist
  built only from tool names that actually exist in
  `apps/cortex-mcp/cortex_mcp/server.py` today (`search_rental_items`,
  `search_customers`, `check_inventory_availability`,
  `create_quote_draft`, `create_customer_draft`,
  `submit_approval_request`, `prepare_owner_statement`). The spec calls
  for three read-only agents (`cortex-returns`, `cortex-approval-
  assistant`, plus part of `cortex-operations`) that need a read-only
  MCP tool that doesn't exist yet — given an empty tool list and
  disclosed as a real gap in `HANDOFF.md`, rather than inventing a
  `read_transaction`-style tool name that isn't real.
- `services/chat_context.py`: `ChatContextResolver` — the actual
  enforcement of "le serveur doit vérifier que l'utilisateur peut voir
  la ressource": `frappe.has_permission()` plus an explicit Company
  match check on the referenced document, raising
  `ChatContextPermissionError` (→ `frappe.PermissionError` in the API
  layer) rather than trusting the client's claim about what it's
  looking at.
- `services/onyx_chat_client.py`: `OnyxChatClient` interface +
  `MockOnyxChatClient` — deterministic, keyword-driven (not random), so
  every response is explicitly labeled as simulated and never fabricates
  a real system fact (e.g. never claims a specific quantity is
  available). This is the one seam a real Onyx-calling client would
  implement later.
- `services/chat_response_transformer.py`: validates every raw block
  through the same `ChatBlock` discriminated union the frontend
  contract is written against (`TypeAdapter`) — a malformed block
  becomes a visible `ErrorBlock`, never a crash or a silently dropped
  answer.
- `services/chat_telemetry.py`: reuses the existing Cortex Agent
  Run/Tool Call trail (`services/agent_telemetry.py`) rather than a
  parallel logging system — required a small, backward-compatible
  change to `record_tool_call()` (added optional `agent_id`/
  `request_id` overrides) since chat calls come from a human Desk
  session, not an MCP call with `X-Cortex-Agent-Id` headers.
- `services/chat_session.py`: `ChatSessionService`, the gateway
  orchestrator — rate limiting via `frappe.cache()` (real Frappe API,
  not guessed), a real no-DB fallback path (same convention as
  `AvailabilityService.check()`'s mock branch) so the full
  validate→route→policy→mock-client→transform pipeline is genuinely
  exercised by tests in this sandbox, not just written and hoped-for.
- `api/v1/chat.py`: `create_session`, `send_message`, `get_session`,
  `list_sessions`, `pin_context`, `clear_context` — all
  `require_human_staff_role` (same gate as `checkin.py`), no MCP tool,
  not part of the agent-facing surface.
- 18 new tests (`test_chat_gateway.py`), 17 running for real in this
  sandbox (client-escalation rejection, agent-router/tool-policy drift
  detection, mock-client labeling, transformer error handling, full
  send-message round trip) plus 1 correctly `skipUnless(frappe, ...)`
  for real cross-user isolation on a live bench.

**Not done in this pass** (tracked in `HANDOFF.md`): no real Onyx HTTP
client, no streaming/SSE, no `CortexCopilotPanel` frontend (separate
PR, stacked on this one), the read-only MCP tool gap above, and no
retention/deletion job for `Cortex Chat Session.retention_until` (field
exists, nothing populates or enforces it yet).

---

## Eighth wave — Cortex Copilot Panel (real backend, mocked Onyx)

**Problem.** Follow-up to the seventh wave, per the user's confirmed
sequencing ("backend first, panel next"). Builds the floating,
non-modal chat panel from the copilot-panel spec — but wired to the
**real** `cortex_rental.api.v1.chat` endpoints from wave seven, not
client-side mock data, since that backend already exists and works.

**New verified pattern**: `app_include_js` referencing a `.bundle.js`
with ESM imports, resolved globally on every Desk page (not just one
Page's own bundle) via `frappe.ready()`. Cross-checked against two
independent searches (Frappe v14 migration notes: `app_include_js`
moved from raw JS paths to bundle references; a Frappe forum thread on
`app_include_js` + `import` + esbuild) before writing
`cortex_copilot.bundle.js` — this is the mechanism that makes the
launcher appear on every page, not just a single Desk Page's route.

**Added.**
- `public/js/cortex_copilot/`: `CortexCopilotPanel.vue` (floating or
  docked mode), `CopilotHeader`/`ContextBar`/`QuickActions`/
  `Conversation`/`Composer`, and eight block renderers — one per real
  `ChatBlock` type from `schemas/chat_schemas.py`
  (`CopilotVerifiedFact`, `CopilotExtractedData`, `CopilotProposalCard`,
  `CopilotApprovalCard`, `CopilotRiskCard`, `CopilotMissingInfoCard`,
  `CopilotToolProgress`, `CopilotErrorCard`) — matching the backend
  contract exactly rather than the slightly different component list
  named in the earlier draft spec, since wave seven's shipped schema is
  the authority now, not a prompt written before it existed.
  `chatClient.js` calls the real endpoints; nothing here fabricates a
  response.
- `public/js/cortex_assistant/` + `cortex_rental/page/cortex_assistant/`:
  the detached `/app/cortex-assistant` Desk Page, same verified
  Vue-in-a-Desk-Page pattern as Disponibilité (fifth wave), hosting the
  same panel component in "docked" mode.
- Global launcher: `hooks.py`'s `app_include_js` +
  `cortex_copilot.bundle.js`, hidden for `Guest` and non-staff roles as
  a client-side courtesy (the real gate stays
  `require_human_staff_role()` server-side, unaffected either way).
- Reuses design-system components directly rather than duplicating them:
  `CortexReadinessIndicator` for approval requirements,
  `CortexErrorState`/`CortexEmptyState`/`CortexLoadingState` for panel
  states — exactly the "don't duplicate Frappe UI/Cortex components"
  rule the design system doc itself states.
- Workspace: added a real "Assistant Cortex" shortcut to
  `/app/cortex-assistant`; relabeled the existing widget shortcut
  "Assistant Onyx (widget, expérimental)" so the two aren't confused —
  one is a real, working chat backed by this wave's gateway, the other
  is the still-unverified `<onyx-chat-widget>` embed from the fourth
  wave.
- `docs/frontend/copilot-panel.md`: full file map, the verified
  `app_include_js`/`frappe.ready()` pattern, and an explicit table of
  what's real vs. a disclosed simplification in this pass (no context
  editor, no live route-change reactivity, proposal/approval buttons
  re-engage the real chat pipeline or navigate to a real existing Form
  rather than opening screens that don't exist yet, no streaming).

**Honesty choices worth calling out**: `CopilotProposalCard`'s primary
button does not create anything — there is no Transaction Composer yet
to open prefilled, so it re-sends the proposal's own title as the next
message through the real pipeline instead of faking a mutation.
`CopilotApprovalCard`'s button navigates to the real `Approval Request`
Desk Form (which does exist) rather than a fabricated approvals queue
screen.

**Not done in this pass** (tracked in `HANDOFF.md`): no streaming, no
context editor drawer, no live reactivity to Desk navigation while the
panel stays open, and still no real Onyx client underneath any of this
— every response rendered here comes from `MockOnyxChatClient`.

---

## Ninth wave — Copilot panel: context editor + live route reactivity

**Problem.** Two items disclosed as "not built" at the end of the
eighth wave, picked up as a direct continuation: a real context editor
(not a fake one) and live context reactivity as the user navigates
Desk while the panel stays open.

**Verified before writing**: `frappe.router.on('change', ...)` is the
current, real Frappe client event for route changes — cross-checked
against a current forum answer, deliberately not the older
`frappe.route.on(...)` form that also turns up in search results (a
pre-2018, since-refactored API). `frappe.router.off(...)` is called
symmetrically on unmount but only behind a truthiness guard, since its
existence wasn't independently confirmed the way `.on()` was — if
missing, the listener leaks rather than crashing the panel.

**Added.**
- `CortexCopilotPanel.vue`: `frappe.router.on('change', ...)` keeps the
  context bar (and the next message's payload) in sync with Desk
  navigation, without touching any already-sent message.
- `CopilotContextBar.vue`: a real "Modifier le contexte" toggle —
  scoped honestly to the one field this app actually resolves (whether
  the currently open document is included in the next message). No
  checkboxes for "item sélectionné"/"documents ajoutés" from the
  original mockup — nothing produces that selection state in this app
  yet, so no control that would silently do nothing.
- The share/don't-share choice resets to "shared" whenever the
  referenced document itself changes (a per-message decision, not a
  sticky preference that should carry over onto an unrelated document).

**Not done** (still tracked in `HANDOFF.md`): everything from the
eighth wave's remaining list — streaming, wiring proposals to a real
Transaction Composer, and a real Onyx client.

---

## Tenth wave — Cortex Transaction Composer

**Problem.** Continuation of the screen-by-screen build, per the
design spec's own explicit priority order (Disponibilité, then
Composer, then Check-in — Disponibilité and the Copilot Assistant were
already done). `/app/cortex-transaction-composer`: customer search/
create, item search, live pricing, live per-line availability, real
quote creation.

**Almost entirely built on existing backend** — `search_customers`,
`create_customer_draft`, `search_items`, `check_availability`, and
`create_quote_draft` all already existed (from earlier waves/the
original Gemini scaffold) and are gated by `require_agent_scope`,
which already grants access to any `HUMAN_STAFF_ROLES` member — no new
permission plumbing needed, just a real caller.

**One new endpoint**: `api/v1/quotes.py::preview_pricing` — a
read-only twin of the existing `create_draft_handler`, same
`PricingService` calls, nothing persisted. Added because the design
system explicitly forbids computing price in JavaScript ("Le prix est
présenté comme résultat du PricingService, pas comme calcul
frontend") — there was no honest way to show a live price preview
while composing without it. Unlike `create_draft_handler`, a missing
`unit_rate` defaults to `0.0`, not a fabricated `100.0` — a live
preview silently showing a fake $100/day would be worse than an
obviously-wrong $0.

**One real bug fix bundled in**: `create_quote_draft`'s `lines`
argument now gets `frappe.parse_json()`'d when it arrives as a string
— how a browser's `frappe.call()` form-encodes a nested array. This
endpoint had previously only ever been called with a real Python list
(MCP, tests), so this path was untested until a browser caller
actually needed it; it would have silently corrupted every quote a
human created through this page otherwise (iterating a JSON string's
characters instead of its line objects).

**Explicitly not built, and explained why in
`docs/frontend/transaction-composer.md`** rather than left ambiguous:
serial number auto-assignment (a Quote never blocks inventory —
serials are only claimed at Reservation confirmation, so building this
on the Composer would imply a guarantee this state doesn't make),
customer-tier automatic discounts (no such logic exists in
`PricingService`), and a readiness indicator during composition
(`create_draft_handler` always returns all three readiness flags
`false` — nothing computes real readiness before the transaction
exists; shown honestly on the real Form after creation instead).

**Added.**
- `cortex_rental/page/cortex_transaction_composer/` +
  `public/js/cortex_transaction_composer/`: the page, same verified
  Vue-in-a-Desk-Page pattern as every other Cortex screen.
- `public/js/cortex_shared/dateUtils.js`: `fmtDateTime`/`addDays`
  extracted from `CortexAvailability.vue` once a second page needed the
  exact same helper — not introduced speculatively.
- Availability's "+ Créer une soumission" now routes to the Composer
  via `frappe.route_options` (the real Frappe cross-page handoff
  pattern) instead of the raw native `frappe.new_doc()` form it used
  before this page existed.
- Workspace: added a "Nouvelle transaction" shortcut, positioned right
  after Disponibilité to match the priority order.
- 3 new tests (`test_demo_scenario.py`): `preview_pricing` matches
  `create_draft_handler`'s math exactly, requires a date window, and
  defaults a missing rate to `0.0` rather than a fabricated value.

**Not done in this pass** (tracked in `HANDOFF.md`): accessory/kit
suggestions, free-text lines, and permission-gated line-level discount
overrides (this pass's discount field has no permission check at all).

## Eleventh wave — Cortex Accounting / Profit and Loss Statement

**Problem.** `docs/design-system-accounting-pnl.md` specified a full
Accounting/P&L screen but its own architecture section assumed a
Next.js/shadcn stack — this app deliberately has no npm/Vite build
step (`docs/design-system.md` "Packaging"). Confirmed with the user
before building anything: stay on the existing Vue-3-in-a-Desk-Page
pattern, no second frontend stack, same as every other Cortex screen.

**Built on ERPNext's own accounting engine, not a new one.** This app
already depends on `erpnext` (see `HANDOFF.md`'s `bench get-app
erpnext` step), which owns GL Entry, Fiscal Year, and a working
`Profit and Loss Statement` report. `api/v1/accounting.py::
get_profit_and_loss` calls that report's `execute()` and reshapes its
output into the KPI/period/account-tree JSON the screen renders —
reimplementing double-entry P&L math here would have duplicated a
system ERPNext already owns correctly.

**Not verified against a live bench** (same caveat as every other
Frappe/ERPNext integration point in this app — no bench in this
sandbox). The exact column/row field names ERPNext's report returns
(`account`, `account_name`, `indent`, a "Total Income"/"Total Expense"/
"Net Profit" row by name rather than a flag) are documented assumptions
in `accounting.py`'s module docstring, not confirmed output. Only the
pure reshaping logic (`transform_pnl_report`, `_build_pnl_filters`) is
tested here (12 tests, `test_accounting_pnl.py`) — the whitelisted
endpoint itself needs a real bench run to prove ERPNext's actual
version matches these assumptions.

**New finance-only permission gate.** `require_human_staff_role()`
(used everywhere else) grants Counter Staff/Inventory Manager/
Consignment Manager access too — too broad for company-wide financial
statements. Added `require_finance_role()`
(`permissions/agent_scopes.py`), scoped to Operations Manager, Finance
Manager, Account Reviewer, and Rental Manager.

**Two toolbar fields shown disabled, not wired**: `Branch` and `Report
View` from the design mockup have no equivalent ERPNext filter on this
report — same "don't build a dead link" rule already applied to
unwired state tokens in `design-system.md`. `Company` is shown
read-only (resolved server-side via `get_company_context()`), not a
picker — this page doesn't add a second way to select tenant Company.

**Added.**
- `cortex_rental/page/cortex_accounting_pnl/` +
  `public/js/cortex_accounting_pnl/`: the page, same verified
  Vue-in-a-Desk-Page pattern as every other Cortex screen.
- `api/v1/accounting.py`: `get_profit_and_loss` (whitelisted GET),
  plus the pure `_build_pnl_filters`/`transform_pnl_report` functions.
- 4 new shared components (`public/js/cortex_shared/`):
  `CortexKpiSummary`, `CortexFinancialChart` (hand-rolled inline SVG,
  no charting library), `CortexFinancialTable` + `CortexAccountRow`
  (recursive, real `<table>`/`th scope="col"` markup — genuinely
  tabular data, unlike Availability's flex-div calendar grid). Plus
  `formatters.js::formatCurrency`. Documented in
  `docs/design-system-component-contracts.md`.
- `cortex-tokens.css`: `--accounting-income`/`--accounting-expense`/
  `--accounting-profit`, scoped separately from the general Cortex
  indigo brand palette per the spec's distinct 3-color series.
  `cortex-utilities.css`: `.cx-sr-only` (visually-hidden accessible
  fallback, used by the chart's screen-reader data table).
  Buttons/controls on this screen still use the standard
  `--cortex-primary-*` action color, not the spec's separate blue —
  keeps one action color app-wide.
- Workspace: added a "Profit and Loss Statement" shortcut and a Finance
  card link.
- 12 new tests (`test_accounting_pnl.py`), all passing without a
  bench (pure transform/filter logic, synthetic ERPNext-shaped input).
- Finalisation P&L :
  - Menu d'actions et d'export : export CSV direct côté client avec indentation hiérarchique et KPI, vue d'impression et export PDF `@media print` épurée, et lien vers le rapport natif ERPNext.
  - Drill-down interactif : clic sur les comptes feuilles (`type === "account"`) ouvrant le Grand Livre ERPNext (`General Ledger`) préfiltré sur le compte, la société et la période sélectionnée.
  - Autocomplétion native HTML via `<datalist>` pour `Fiscal Year`, `Cost Center`, et `Finance Book` chargées dynamiquement depuis l'API Frappe.
  - Sélecteur d'états financiers (*Profit and Loss Statement* actif, *Balance Sheet* et *Cash Flow* réservés).

## Twelfth wave — Cortex Check-in Scanner & Equipment Returns (PRD-RET)

**Scope & Design Decisions.**
Aligned with the user through a structured interview (`/grill-me`):
- Dedicated native Frappe Desk Page `/app/cortex-checkin` using Vue 3 SFC (same zero-npm verified pattern).
- Continuous 3-step workflow without blocking modals:
  1. *Live Scan & Colisage* (Fast scan bar, synthesized Web Audio feedback, auto-match serials, steppers for bulk non-serialized items).
  2. *Diagnostic & Revue des Écarts* (Technical inspection cards for Damaged/Quarantine/Missing items, severity, damage type, estimated repair cost).
  3. *Bilan, Relevé de Restitution & Clôture* (Summary KPIs, double option for partial vs loss-settled return, print-ready Return Receipt).
- Multi-tenant scoping via `get_company_context()` and idempotent write protection (`with_idempotency`).

**Added.**
- `cortex_rental/page/cortex_checkin/` + `public/js/cortex_checkin/`: Desk page and Vue 3 application bundle.
- `services/checkin.py`: `search_active_transactions`, `lookup_scan_target`, and `process_checkin`.
- `api/v1/checkin.py`: endpoints `get_active_transactions`, `lookup_scan`, and `submit_checkin`.
- `cortex_check_in.json` & `cortex_check_in_item.json`: DocType fields for damage severity, damage type, estimated repair costs, and finalization modes.
- `cortex_rental_transaction.js`: "Effectuer le Check-in" action button on the Desk form when in `Checked Out` state.
- `cortex-rental.json`: Added "Check-in & Retours" shortcut and Operations card link.
- `test_checkin_api.py`: Unit tests for handlers, parsing, scan lookup, and mock checkin processing (85 tests passing total).
- `docs/frontend/checkin-scanner.md`: Complete frontend contract and architecture guide.

## Thirteenth wave — SaaS-Grade Hardening, Universal Deployment Script & Demo Fixtures

**Scope & Architecture Decisions.**
- **Backend Performance**: Batch SQL queries in `availability.py` (`GROUP BY item_code`) and `services/checkin.py` (`search_active_transactions`), eliminating N+1 loops.
- **Deep Multi-tenant Isolation**: Strict tenant boundary assertions on all serial numbers and transaction items in `process_checkin`.
- **Frontend SaaS Finish**: Reusable reactive `toastBus.js` / `CortexToast.vue` for non-blocking feedback and `cx-tabular-nums` typography.
- **Universal Deployment Script (`./bin/deploy.sh`)**: Multi-target deployment script supporting `tour` (native bench), `docker` (complete Compose stack), and `fixtures`.
- **Demo Fixtures Generator (`cortex_rental/fixtures/demo_data.py`)**: Idempotent generator creating a full cinema rental company ("Cortex Cinema Rentals"), customer ("Dune 3 Productions"), camera/optics catalog with real serial numbers, and live transactions across all lifecycle states.

**Added.**
- `bin/deploy.sh`: Turnkey deployment script with interactive prompts and `--with-fixtures` / `--skip-fixtures` flags.
- `cortex_rental/fixtures/demo_data.py`: Frappe bench fixture generator (`bench execute cortex_rental.fixtures.demo_data.provision_demo_data`).
- `test_demo_fixtures.py`: Unit tests for demo fixtures provisioning (87/87 tests passing).
- `public/js/cortex_shared/toastBus.js` & `CortexToast.vue`: Centralized reactive toast notifications system.
