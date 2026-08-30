app_name = "cortex_rental"
app_title = "Cortex Rental"
app_publisher = "Cortex AI-Native ERP Team"
app_description = "AI-Native Rental, Availability & Consignment Management for Frappe & ERPNext"
app_email = "architecture@cortex.local"
app_license = "proprietary"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/cortex_rental/css/cortex_rental.css"
# app_include_js = "/assets/cortex_rental/js/cortex_rental.js"

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
