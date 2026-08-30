# apps/cortex_rental/cortex_rental/permissions/__init__.py
"""
Permission query hooks for Cortex Rental — enforces row-level multi-tenant
isolation for every Company-scoped DocType. Registered per-doctype in
hooks.py under `permission_query_conditions`.
"""

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_allowed_companies


def _company_scoped_condition(user: str, doctype: str) -> str:
    if not frappe:
        return ""

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return ""

    allowed = get_allowed_companies(user)
    if not allowed:
        # No authorized Company for this identity => no visible rows.
        return "1=0"

    companies = ", ".join(frappe.db.escape(c) for c in allowed)
    return f"`tab{doctype}`.`company` in ({companies})"


def get_permission_query_conditions(user: str) -> str:
    """Kept for backward compatibility; prefer the doctype-specific
    wrappers below, each of which is registered explicitly in hooks.py
    so the correct table name is always used."""
    return ""


def audit_event_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Audit Event")


def approval_request_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Approval Request")


def consignment_owner_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Consignment Owner")


def consignment_payout_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Consignment Payout")


def cortex_inbound_request_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Cortex Inbound Request")


def cortex_rental_transaction_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Cortex Rental Transaction")


def rental_pricing_rule_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Rental Pricing Rule")


def cortex_rental_item_profile_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Cortex Rental Item Profile")


def customer_query_conditions(user: str) -> str:
    """
    Core ERPNext `Customer` is not natively Company-scoped. Cortex adds a
    `cortex_company` Custom Field (see fixtures/custom_field.json) and
    filters on it here so tenants never see each other's customer list.
    """
    if not frappe:
        return ""

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return ""

    allowed = get_allowed_companies(user)
    if not allowed:
        return "1=0"

    companies = ", ".join(frappe.db.escape(c) for c in allowed)
    return f"`tabCustomer`.`cortex_company` in ({companies})"


def cortex_idempotency_record_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Cortex Idempotency Record")


def cortex_agent_run_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Cortex Agent Run")


def cortex_agent_tool_call_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Cortex Agent Tool Call")


def cortex_evidence_reference_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Cortex Evidence Reference")


def cortex_extraction_run_query_conditions(user: str) -> str:
    return _company_scoped_condition(user, "Cortex Extraction Run")
