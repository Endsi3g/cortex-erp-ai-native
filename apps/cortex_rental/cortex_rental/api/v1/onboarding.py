"""Company onboarding endpoints (authenticated, company-scoped). Rules live in services/onboarding.py."""

from typing import Any, Callable, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.api.v1._shared import envelope
from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services import onboarding
from cortex_rental.services import defense
from cortex_rental.services.signup_rules import SignupError


def guarded(action: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    try:
        return envelope({"ok": True, **action()})
    except SignupError as error:
        return envelope({"ok": False, "code": error.code, "message": str(error)})


if frappe:

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_onboarding():
        require_human_staff_role()
        company = get_company_context()
        return envelope(onboarding.get_state(company))

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("onb_company", 60)
    def save_company_profile(
        country: str = "",
        default_currency: str = "",
        address_line1: str = "",
        city: str = "",
        state: str = "",
        pincode: str = "",
        phone_no: str = "",
        email: str = "",
        website: str = "",
        tax_id: str = "",
    ):
        require_human_staff_role()
        data = {
            "country": country,
            "default_currency": default_currency,
            "address_line1": address_line1,
            "city": city,
            "state": state,
            "pincode": pincode,
            "phone_no": phone_no,
            "email": email,
            "website": website,
            "tax_id": tax_id,
        }
        return guarded(lambda: {"state": onboarding.save_company_profile(get_company_context(), data)})

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("onb_owner", 60)
    def save_owner_profile(first_name: str = "", last_name: str = "", mobile_no: str = "", time_zone: str = ""):
        require_human_staff_role()
        data = {"first_name": first_name, "last_name": last_name, "mobile_no": mobile_no, "time_zone": time_zone}
        return guarded(lambda: {"state": onboarding.save_owner_profile(get_company_context(), data)})

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("onb_pricing", 60)
    def save_pricing(tps_number: str = "", tvq_number: str = "", deposit_percent: str = "30"):
        require_human_staff_role()
        data = {"tps_number": tps_number, "tvq_number": tvq_number, "deposit_percent": deposit_percent}
        return guarded(lambda: {"state": onboarding.save_pricing(get_company_context(), data)})

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def skip_step(step: str = ""):
        require_human_staff_role()
        return guarded(lambda: {"state": onboarding.skip_step(get_company_context(), step)})

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("invite", 30)
    def invite_team_member(email: str = "", full_name: str = "", preset: str = ""):
        require_human_staff_role()
        return guarded(lambda: onboarding.invite_team_member(get_company_context(), email, full_name, preset))

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def complete_step(step: str = ""):
        require_human_staff_role()
        return guarded(lambda: {"state": onboarding.complete_step(get_company_context(), step)})

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("onb_finish", 20)
    def finish_onboarding():
        require_human_staff_role()
        return guarded(lambda: {"state": onboarding.finish(get_company_context())})

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
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
    @defense.safe_input
    def post_login_route():
        """Where the browser goes right after a password is set: the setup assistant for an owner, else the app."""
        require_human_staff_role()
        return {"route": onboarding_route(frappe.session.user)}


def onboarding_route(user: str) -> str:
    """Where to go once the password is set: the Cortex Rental workspace (it shows the setup guide for an owner)."""
    return "/app/cortex-rental"
