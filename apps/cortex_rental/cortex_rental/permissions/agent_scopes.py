"""
Agent scope validation and security enforcement.
Ensures agent requests carry authorized scopes and run within tenant company context.
"""
from typing import Optional

try:
    import frappe
except ImportError:
    frappe = None


def require_agent_scope(required_scope: str) -> None:
    """
    Validate that current user/session possesses the required scope or role.
    Throws PermissionError if unauthorized.
    """
    if not frappe:
        return

    user = frappe.session.user
    roles = frappe.get_roles(user)

    # System Manager / Administrator bypass
    if "System Manager" in roles or user == "Administrator":
        return

    # Check for Agent Service Account role
    if "Agent Service Account" not in roles and "Rental Operator" not in roles:
        frappe.throw(
            f"Unauthorized: Access requires role 'Agent Service Account' or scope '{required_scope}'.",
            frappe.PermissionError
        )


def get_company_context(company_header: Optional[str] = None) -> str:
    """
    Resolve tenant company context strictly from header or authenticated user default.
    """
    if not frappe:
        return company_header or "CineRental Montreal"

    company = company_header or (
        hasattr(frappe.local, "request") and frappe.local.request and
        frappe.local.request.headers.get("X-Company-ID")
    ) or frappe.defaults.get_user_default("Company")

    if not company:
        frappe.throw("Multi-Tenant Error: Company context (X-Company-ID) is strictly required.", frappe.PermissionError)

    return str(company)
