"""Authenticated session context for the Cortex Vue client."""

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import FINANCE_STAFF_ROLES


if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_session_context():
        user = frappe.session.user
        if not user or user == "Guest":
            frappe.throw("Authentication is required.", frappe.AuthenticationError)
        roles = frappe.get_roles(user)
        companies = frappe.get_list("Company", fields=["name", "default_currency"], order_by="name asc")
        default_company = frappe.defaults.get_user_default("Company", user) or frappe.defaults.get_global_default(
            "company"
        )
        visible = {row.name for row in companies}
        if default_company not in visible:
            default_company = companies[0].name if companies else None
        permissions = {
            "cortex:operations:view": frappe.has_permission("Cortex Rental Transaction", "read"),
            "cortex:availability:view": frappe.has_permission("Cortex Rental Item Profile", "read"),
            "cortex:rental:view": frappe.has_permission("Cortex Rental Transaction", "read"),
            "cortex:quote:create": frappe.has_permission("Cortex Rental Transaction", "create"),
            "cortex:checkout:perform": frappe.has_permission("Cortex Rental Transaction", "write"),
            "cortex:checkin:perform": frappe.has_permission("Cortex Check-In", "create"),
            "cortex:approvals:decide": bool(
                set(roles)
                & {
                    "System Manager",
                    "Administrator",
                    "Rental Manager",
                    "Cortex Account Reviewer",
                }
            ),
            "cortex:catalog:view": frappe.has_permission("Cortex Rental Item Profile", "read"),
            "cortex:catalog:manage": frappe.has_permission("Cortex Rental Item Profile", "write"),
            "cortex:serial:view": frappe.has_permission("Serial No", "read"),
            "cortex:consignment:view": frappe.has_permission("Consignment Owner", "read"),
            "cortex:consignment:finance": frappe.has_permission("Consignment Payout", "read"),
            "cortex:intake:view": frappe.has_permission("Cortex Inbound Request", "read"),
            "cortex:drafts:review": frappe.has_permission("Cortex Extraction Run", "read"),
            "cortex:telemetry:admin": bool(set(roles) & {"System Manager", "Administrator"}),
            "cortex:copilot:access": frappe.has_permission("Cortex Chat Session", "create"),
            "cortex:policies:view": frappe.has_permission("Rental Pricing Rule", "read"),
            "cortex:team:manage": bool(set(roles) & {"System Manager", "Administrator"}),
            "cortex:migration:run": bool(set(roles) & {"System Manager", "Cortex System Manager", "Administrator"}),
            "cortex:audit:view": frappe.has_permission("Audit Event", "read"),
            # Same rule as require_finance_role(), so the menu and the API agree.
            "cortex:finance:view": bool(
                set(roles) & ({"System Manager", "Administrator", "Cortex System Manager"} | set(FINANCE_STAFF_ROLES))
            ),
        }
        return {
            "data": {
                "user": {
                    "id": user,
                    "email": user,
                    "full_name": frappe.utils.get_fullname(user),
                    "roles": roles,
                },
                "companies": [
                    {
                        "id": row.name,
                        "name": row.name,
                        "code": row.name,
                        "is_default": row.name == default_company,
                        "currency": row.default_currency or "CAD",
                    }
                    for row in companies
                ],
                "active_company_id": default_company,
                "permissions": permissions,
            }
        }
