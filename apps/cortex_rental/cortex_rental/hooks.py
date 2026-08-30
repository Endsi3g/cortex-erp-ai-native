app_name = "cortex_rental"
app_title = "Cortex Rental"
app_publisher = "Cortex AI-Native ERP Team"
app_description = "AI-Native Rental, Availability & Consignment Management for Frappe & ERPNext"
app_email = "architecture@cortex.local"
app_license = "proprietary"

# Branding — placeholder mark (see docs/design-system.md "Branding
# Frappe"); `app_logo_url`/`app_icon`/`app_color` are real hooks.py keys
# (verified against docs.frappe.io/framework/user/en/python-api/hooks),
# not guessed. This does not touch any core Frappe file.
app_logo_url = "/assets/cortex_rental/images/cortex-logo.svg"
app_icon = "octicon octicon-briefcase"
app_color = "#4F46E5"

# Includes in <head>
# ------------------

# Cortex Operations System design tokens/theme/utilities — plain CSS,
# no build step (see cortex-tokens.css header for why). Injected into
# desk.html only, never web.html — this app has no public-facing pages
# beyond the one authenticated www/onyx-assistant.html, which loads its
# own styling and isn't part of the Desk chrome these files target.
app_include_css = [
    "/assets/cortex_rental/css/cortex-tokens.css",
    "/assets/cortex_rental/css/cortex-theme.css",
    "/assets/cortex_rental/css/cortex-utilities.css",
]

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
    "Customer": "cortex_rental.permissions.customer_query_conditions",
    "Cortex Idempotency Record": "cortex_rental.permissions.cortex_idempotency_record_query_conditions",
    "Cortex Agent Run": "cortex_rental.permissions.cortex_agent_run_query_conditions",
    "Cortex Agent Tool Call": "cortex_rental.permissions.cortex_agent_tool_call_query_conditions",
    "Cortex Evidence Reference": "cortex_rental.permissions.cortex_evidence_reference_query_conditions",
    "Cortex Extraction Run": "cortex_rental.permissions.cortex_extraction_run_query_conditions",
    "Cortex Check-In": "cortex_rental.permissions.cortex_check_in_query_conditions",
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
