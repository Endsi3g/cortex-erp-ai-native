app_name = "cortex_rental"
app_title = "Cortex Rental"
app_publisher = "Cortex AI-Native ERP Team"
app_description = "AI-Native Rental, Availability & Consignment Management"
app_email = "architecture@cortex.local"
app_license = "proprietary"
required_apps = ["erpnext"]

# Branding — "Return ring" mark (docs/brand/logo-kit/GUIDELINES.md); the logo file is
# the small-size cut. `app_logo_url`/`app_icon`/`app_color` are real hooks.py keys
# (verified against docs.frappe.io/framework/user/en/python-api/hooks),
# not guessed. This does not touch any core Frappe file.
app_logo_url = "/assets/cortex_rental/images/cortex-logo.svg"
app_icon = "octicon octicon-briefcase"
app_color = "#047857"

# Includes in <head>
# ------------------

# Cortex Operations System design tokens/theme/utilities — plain CSS,
# no build step (see cortex-tokens.css header for why). Injected into
# desk.html only, never web.html — this app has no public-facing pages
# beyond the one authenticated www/onyx-assistant.html, which loads its
# own styling and isn't part of the Desk chrome these files target.
website_route_rules = [
    {"from_route": "/devis/<token>", "to_route": "devis"},
    {"from_route": "/demande/<slug>", "to_route": "demande"},
    {"from_route": "/suivi/<token>", "to_route": "suivi"},
]

app_include_css = [
    "/assets/cortex_rental/css/cortex-tokens.css",
    "/assets/cortex_rental/css/cortex-theme.css",
    "/assets/cortex_rental/css/cortex-utilities.css",
    "/assets/cortex_rental/css/cortex-home.css",
    "/assets/cortex_rental/css/cortex-motion.css",
    "/assets/cortex_rental/css/cortex-nav.css",
    "/assets/cortex_rental/css/cortex-a11y.css",
    "/assets/cortex_rental/css/cortex-mobile.css",
    "/assets/cortex_rental/css/cortex-account.css",
    "/assets/cortex_rental/css/cortex-dossier.css",
    "/assets/cortex_rental/css/cortex-onboarding.css",
    "/assets/cortex_rental/css/cortex-desk-fixes.css",
]

# Global floating Cortex Copilot launcher — mounted on every Desk page
# on the Desk `startup` event (see cortex_copilot.bundle.js). Verified real
# pattern: app_include_js can reference a .bundle.js with ESM imports,
# resolved by the same esbuild pipeline that compiles a Desk Page's own
# .bundle.js (docs.frappe.io + frappe/frappe wiki, cross-checked before
# use — see CHANGELOG.md, eighth wave).
app_include_js = [
    "cortex_copilot.bundle.js",
    "/assets/cortex_rental/js/cortex_desk.js",
    "/assets/cortex_rental/js/cortex_nav.js",
    "/assets/cortex_rental/js/cortex_loading.js",
    "/assets/cortex_rental/js/cortex_pages.js",
    "/assets/cortex_rental/js/cortex_policy.js",
    "/assets/cortex_rental/js/cortex_dossier.js",
    "/assets/cortex_rental/js/cortex_export.js",
    "/assets/cortex_rental/js/cortex_views.js",
    "/assets/cortex_rental/js/cortex_a11y.js",
    "/assets/cortex_rental/js/cortex_i18n.js",
]

# Fiche client 360° (devis ouverts, locations en cours, solde dû).
doctype_js = {"Customer": "public/js/cortex_customer.js"}

# Visitors who are not signed in get French pages (see auth_hooks.french_for_guests).
before_request = ["cortex_rental.auth_hooks.french_for_guests", "cortex_rental.services.defense.request_brake"]

# En-têtes de sécurité sur chaque réponse (voir services/defense.py).
after_request = ["cortex_rental.services.defense.security_headers", "cortex_rental.services.defense.normalize_lockout"]

# DocType Events (Audit logging & validation hooks)
# ------------------------------------------------
# NOTE: a `doc_events` block referencing
# cortex_rental.overrides.{quotation,sales_order,serial_no} previously
# lived here, but no `apps/cortex_rental/cortex_rental/overrides/`
# module exists anywhere in this app — `bench migrate` / app boot would
# fail on the dangling import. Nothing in this codebase or its tests
# relies on it. Removed rather than fabricated (no spec exists for what
# these overrides should do) — implementing real Quotation/Sales
# Order/Serial No override behavior is an open follow-up, not something
# to invent here.
doc_events = {}

# Rappels : retenues qui expirent, retours en retard, devis sans réponse, factures échues (services/reminders.py).
scheduler_events = {
    "hourly": ["cortex_rental.services.reminders.hourly"],
    "daily": ["cortex_rental.services.devices.prune"],
}

# Appareils connectés : on garde l'agent utilisateur à l'ouverture de chaque session (services/devices.py).
on_session_creation = ["cortex_rental.services.devices.on_login"]

# Permission Query Hooks for Multi-Tenancy
# ----------------------------------------
# Each entry MUST point to a doctype-specific wrapper (not the generic
# no-op) so the row-level Company filter is actually applied. See
# cortex_rental/permissions/__init__.py.
permission_query_conditions = {
    "Audit Event": "cortex_rental.permissions.audit_event_query_conditions",
    "Approval Request": "cortex_rental.permissions.approval_request_query_conditions",
    "Consignment Owner": "cortex_rental.permissions.consignment_owner_query_conditions",
    "Consignment Payout": "cortex_rental.permissions.consignment_payout_query_conditions",
    "Cortex Inbound Request": "cortex_rental.permissions.cortex_inbound_request_query_conditions",
    "Cortex Rental Transaction": "cortex_rental.permissions.cortex_rental_transaction_query_conditions",
    "Rental Pricing Rule": "cortex_rental.permissions.rental_pricing_rule_query_conditions",
    "Cortex Rental Item Profile": "cortex_rental.permissions.cortex_rental_item_profile_query_conditions",
    "Cortex Rental Invoice": "cortex_rental.permissions.cortex_rental_invoice_query_conditions",
    "Cortex Rental Payment": "cortex_rental.permissions.cortex_rental_payment_query_conditions",
    "Cortex Finance Settings": "cortex_rental.permissions.cortex_finance_settings_query_conditions",
    "Cortex Support Request": "cortex_rental.permissions.cortex_support_request_query_conditions",
    "Cortex Journal Entry": "cortex_rental.permissions.cortex_journal_entry_query_conditions",
    "Cortex AI Usage": "cortex_rental.permissions.cortex_ai_usage_query_conditions",
    "Customer": "cortex_rental.permissions.customer_query_conditions",
    "Cortex Idempotency Record": "cortex_rental.permissions.cortex_idempotency_record_query_conditions",
    "Cortex Agent Run": "cortex_rental.permissions.cortex_agent_run_query_conditions",
    "Cortex Agent Tool Call": "cortex_rental.permissions.cortex_agent_tool_call_query_conditions",
    "Cortex Evidence Reference": "cortex_rental.permissions.cortex_evidence_reference_query_conditions",
    "Cortex Extraction Run": "cortex_rental.permissions.cortex_extraction_run_query_conditions",
    "Cortex Check-In": "cortex_rental.permissions.cortex_check_in_query_conditions",
    "Cortex Onboarding": "cortex_rental.permissions.cortex_onboarding_query_conditions",
    "Cortex Chat Session": "cortex_rental.permissions.cortex_chat_session_query_conditions",
    "Cortex Chat Message": "cortex_rental.permissions.cortex_chat_message_query_conditions",
    "Cortex Chat Context Snapshot": "cortex_rental.permissions.cortex_chat_context_snapshot_query_conditions",
}

# Fixtures exported/synced on `bench migrate` — provisions the granular
# Cortex roles referenced by permissions/agent_scopes.py and the Cortex
# Company scoping custom field on the core ERPNext Customer doctype.
fixtures = [
    {"dt": "Role", "filters": [["role_name", "like", "Cortex %"]]},
    {
        "dt": "Custom Field",
        "filters": [["name", "in", ["Customer-cortex_company", "Serial No-cortex_status"]]],
    },
]

# Lifecycle Hooks & Schema Prerequisites
# Navigation lives in the Workspace JSON files (workspace/*), synced by `bench migrate`.
# No boot-time database writes and no sidebar filtering: ERPNext workspaces stay visible.
before_migrate = "cortex_rental.setup.before_migrate"
after_migrate = "cortex_rental.setup.after_migrate"
after_install = "cortex_rental.setup.after_install"

# Login experience: access-request form on the login page, and a read-only boot flag that points the Desk at the
# AI-first home page `cortex-home` (see auth_hooks.py and public/js/cortex_desk.js). The boot hook never writes
# to the database.
signup_form_template = ["cortex_rental.auth_hooks.signup_form_path"]
boot_session = "cortex_rental.auth_hooks.boot_session"
