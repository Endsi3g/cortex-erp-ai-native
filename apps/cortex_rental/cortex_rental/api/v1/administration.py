"""Administration endpoints: pricing rules, team and roles, imports overview. Rules live in services/administration.py."""

from typing import Any, Callable, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.api.v1._shared import envelope
from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services import administration
from cortex_rental.services import defense
from cortex_rental.services.signup_rules import SignupError


def guarded(action: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """A rule failure becomes `{ok: false, code, message}` for inline display; anything else stays an error."""
    try:
        return envelope({"ok": True, **action()})
    except SignupError as error:
        return envelope({"ok": False, "code": error.code, "message": str(error)})


if frappe:

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_pricing():
        require_human_staff_role()
        if not frappe.has_permission("Rental Pricing Rule", "read"):
            frappe.throw("Votre rôle ne permet pas de consulter les règles tarifaires.", frappe.PermissionError)
        return envelope(administration.get_pricing(get_company_context()))

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("pricing_rule", 120)
    def save_pricing_rule(
        name: str = "",
        rule_name: str = "",
        calendar_days: int = 0,
        billable_days: float = 0,
        description: str = "",
        is_active: int = 1,
    ):
        require_human_staff_role()
        data = {
            "name": name,
            "rule_name": rule_name,
            "calendar_days": calendar_days,
            "billable_days": billable_days,
            "description": description,
            "is_active": is_active,
        }
        return guarded(lambda: {"state": administration.save_pricing_rule(get_company_context(), data)})

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def set_pricing_rule_active(name: str = "", active: int = 1):
        require_human_staff_role()
        return guarded(
            lambda: {"state": administration.set_pricing_rule_active(get_company_context(), name, bool(int(active)))}
        )

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_team():
        require_human_staff_role()
        if not administration.can_manage_team(frappe.session.user):
            frappe.throw("Votre rôle ne permet pas de consulter l'équipe.", frappe.PermissionError)
        return envelope(administration.get_team(get_company_context()))

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("member_preset", 120)
    def set_member_preset(email: str = "", preset: str = ""):
        require_human_staff_role()
        return guarded(lambda: {"state": administration.set_member_preset(get_company_context(), email, preset)})

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("member_enabled", 60)
    def set_member_enabled(email: str = "", enabled: int = 1):
        require_human_staff_role()
        return guarded(
            lambda: {"state": administration.set_member_enabled(get_company_context(), email, bool(int(enabled)))}
        )

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("logo", 30)
    def set_company_logo(file_url: str = ""):
        require_human_staff_role()
        return guarded(lambda: administration.set_company_logo(get_company_context(), file_url))

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def team_devices():
        require_human_staff_role()
        return guarded(lambda: administration.team_devices(get_company_context()))

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("sign_out_member", 60)
    def sign_out_member(email: str = "", device_id: str = ""):
        require_human_staff_role()
        return guarded(lambda: administration.sign_out_member(get_company_context(), email, device_id))

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_imports():
        require_human_staff_role()
        if not frappe.has_permission("Data Import", "read"):
            frappe.throw("Votre rôle ne permet pas de consulter les imports.", frappe.PermissionError)
        return envelope(administration.get_imports(get_company_context()))
