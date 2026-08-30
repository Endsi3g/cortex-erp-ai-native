# Changelog — Cortex Security & Correctness Remediation

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
