"""Company onboarding endpoints (authenticated, company-scoped). Rules live in services/onboarding.py."""

from typing import Any, Callable, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.api.v1._shared import envelope
from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services import onboarding
from cortex_rental.services.signup_rules import SignupError


def guarded(action: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    try:
        return envelope({"ok": True, **action()})
    except SignupError as error:
        return envelope({"ok": False, "code": error.code, "message": str(error)})


if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_onboarding():
        require_human_staff_role()
        company = get_company_context()
        return envelope(onboarding.get_state(company))

    @frappe.whitelist(methods=["POST"])
    def save_company_profile(
        country: str = "",
        default_currency: str = "",
        tax_id: str = "",
        phone_no: str = "",
        website: str = "",
        time_zone: str = "",
        language: str = "",
    ):
        require_human_staff_role()
        data = {
            "country": country,
            "default_currency": default_currency,
            "tax_id": tax_id,
            "phone_no": phone_no,
            "website": website,
            "time_zone": time_zone,
            "language": language,
        }
        return guarded(lambda: {"state": onboarding.save_company_profile(get_company_context(), data)})

    @frappe.whitelist(methods=["POST"])
    def invite_team_member(email: str = "", full_name: str = "", preset: str = ""):
        require_human_staff_role()
        return guarded(lambda: onboarding.invite_team_member(get_company_context(), email, full_name, preset))

    @frappe.whitelist(methods=["POST"])
    def complete_step(step: str = ""):
        require_human_staff_role()
        return guarded(lambda: {"state": onboarding.complete_step(get_company_context(), step)})

    @frappe.whitelist(methods=["POST"])
    def finish_onboarding():
        require_human_staff_role()
        return guarded(lambda: {"state": onboarding.finish(get_company_context())})

    @frappe.whitelist(methods=["GET"])
    def list_choices():
        """Countries, currencies and languages for the profile form (read-only reference data)."""
        require_human_staff_role()
        return envelope(
            {
                "countries": frappe.get_all("Country", pluck="name", order_by="name asc", limit_page_length=300),
                "currencies": frappe.get_all(
                    "Currency", filters={"enabled": 1}, pluck="name", order_by="name asc", limit_page_length=300
                ),
                "languages": [
                    {"name": "fr", "label": "Français"},
                    {"name": "en", "label": "English"},
                ],
            }
        )

    @frappe.whitelist(methods=["GET"])
    def post_login_route():
        """Where the browser goes right after a password is set: the setup assistant for an owner, else the Desk."""
        require_human_staff_role()
        return {"route": onboarding_route(frappe.session.user)}


def onboarding_route(user: str) -> str:
    from cortex_rental.auth_hooks import ONBOARDING_ROUTE

    return ONBOARDING_ROUTE if onboarding.needs_onboarding(user) else "/app"
