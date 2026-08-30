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
doc_events = {
    "Quotation": {
        "before_save": "cortex_rental.overrides.quotation.before_save_quotation",
        "on_submit": "cortex_rental.overrides.quotation.on_submit_quotation",
    },
    "Sales Order": {
        "before_save": "cortex_rental.overrides.sales_order.before_save_sales_order",
        "on_submit": "cortex_rental.overrides.sales_order.on_submit_sales_order",
    },
    "Serial No": {
        "before_save": "cortex_rental.overrides.serial_no.before_save_serial_no",
    }
}

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
    "Rental Item": "cortex_rental.permissions.rental_item_query_conditions",
    "Rental Pricing Rule": "cortex_rental.permissions.rental_pricing_rule_query_conditions",
    "Cortex Rental Item Profile": "cortex_rental.permissions.cortex_rental_item_profile_query_conditions",
    "Customer": "cortex_rental.permissions.customer_query_conditions",
}

# Fixtures exported/synced on `bench migrate` — provisions the granular
# Cortex roles referenced by permissions/agent_scopes.py and the Cortex
# Company scoping custom field on the core ERPNext Customer doctype.
fixtures = [
    {"dt": "Role", "filters": [["role_name", "like", "Cortex %"]]},
    {"dt": "Custom Field", "filters": [["name", "=", "Customer-cortex_company"]]},
]
