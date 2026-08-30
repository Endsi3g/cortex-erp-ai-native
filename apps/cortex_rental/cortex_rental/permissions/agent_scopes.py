"""
Agent scope validation and tenant-context resolution.

SECURITY INVARIANT (PRD multi-tenant strict, §2.5):
`X-Company-ID` (or any client/agent-supplied company argument) is never
trusted as a source of truth. It is at most a routing hint that must
already belong to the authenticated identity's authorized Company set
(resolved server-side via Frappe `User Permission`), or the request is
rejected. The same rule applies to per-tool agent scopes: the role gate
is keyed off the actual `required_scope` requested, not a single coarse
"is this any kind of agent" check.
"""

from typing import List, Optional

try:
    import frappe
except ImportError:
    frappe = None


# Maps each granular agent capability scope to the Frappe Roles allowed to
# exercise it. Keep in sync with docs/PRD §5 role list and
# apps/cortex-onyx/policies/permissions_tools_matrix.md.
SCOPE_ROLE_MAP = {
    "agent:items:read": [
        "Cortex Agent Intake",
        "Cortex Agent Availability",
        "Cortex Agent Reporting",
    ],
    "agent:customers:read": ["Cortex Agent Intake"],
    "agent:customers:draft": ["Cortex Agent Intake"],
    "agent:availability:read": ["Cortex Agent Intake", "Cortex Agent Availability"],
    "agent:quote:draft": ["Cortex Agent Intake"],
    "agent:approval:submit": [
        "Cortex Agent Intake",
        "Cortex Agent Availability",
        "Cortex Agent Reporting",
    ],
    "agent:consignment:read": ["Cortex Agent Reporting"],
}

# Human operational roles reuse the same whitelisted business endpoints as
# agents (PRD principle: "mêmes règles humains et agents") and are not
# subject to the granular per-tool agent scope map.
HUMAN_STAFF_ROLES = [
    "Cortex Operations Manager",
    "Cortex Counter Staff",
    "Cortex Inventory Manager",
    "Cortex Finance Manager",
    "Cortex Consignment Manager",
    "Cortex Account Reviewer",
    "Rental Manager",
    "Rental Operator",
]


def require_agent_scope(required_scope: str) -> None:
    """
    Validate that the current session holds a role authorized for the
    specific `required_scope`. Unlike a coarse "any Agent Service Account
    role" check, this enforces the per-tool allowlist from SCOPE_ROLE_MAP.
    """
    if not frappe:
        return

    user = frappe.session.user
    roles = set(frappe.get_roles(user))

    if user == "Administrator" or "System Manager" in roles or "Cortex System Manager" in roles:
        return

    if roles & set(HUMAN_STAFF_ROLES):
        return

    allowed_roles = set(SCOPE_ROLE_MAP.get(required_scope, []))
    if not allowed_roles or not (roles & allowed_roles):
        frappe.throw(
            f"Unauthorized: scope '{required_scope}' requires one of the roles "
            f"{sorted(allowed_roles) or '[undefined scope]'}.",
            frappe.PermissionError,
        )


def get_allowed_companies(user: Optional[str] = None) -> List[str]:
    """
    Resolve the set of Companies a given identity (human user or agent
    service account) is authorized to act on. This is the single source
    of truth for tenant scoping — derived server-side from Frappe's
    standard `User Permission` (allow="Company") mechanism, never from a
    client-supplied header, prompt, or tool-call argument.
    """
    if not frappe:
        return ["CineRental Montreal"]

    user = user or frappe.session.user

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return frappe.get_all("Company", pluck="name")

    allowed = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Company"},
        pluck="for_value",
    )
    if allowed:
        return list(dict.fromkeys(allowed))

    default = frappe.defaults.get_user_default("Company", user)
    return [default] if default else []


def get_company_context(company_header: Optional[str] = None) -> str:
    """
    Resolve tenant Company context strictly server-side.

    `company_header` (typically the `X-Company-ID` request header) is at
    best a routing hint. It is only accepted if it is already a member of
    the authenticated identity's authorized Company set — never as an
    unverified source of truth. An identity authorized for exactly one
    Company does not need to supply a hint at all.
    """
    if not frappe:
        return company_header or "CineRental Montreal"

    if company_header is None:
        request = getattr(frappe.local, "request", None)
        company_header = request.headers.get("X-Company-ID") if request else None

    allowed = get_allowed_companies()

    if not allowed:
        frappe.throw(
            "Multi-Tenant Error: no Company is authorized for this identity.",
            frappe.PermissionError,
        )

    if not company_header:
        if len(allowed) == 1:
            return allowed[0]
        frappe.throw(
            "Multi-Tenant Error: Company context (X-Company-ID) is required "
            "when an identity is authorized for more than one Company.",
            frappe.PermissionError,
        )

    if company_header not in allowed:
        frappe.throw(
            "Multi-Tenant Error: requested Company is not authorized for this identity.",
            frappe.PermissionError,
        )

    return company_header
