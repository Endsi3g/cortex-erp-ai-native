"""Hook targets for the login experience: signup form template and the onboarding flag."""

try:
    import frappe
except ImportError:
    frappe = None

ONBOARDING_ROUTE = "/app/cortex-company-setup"
SIGNUP_TEMPLATE = "cortex_rental/templates/includes/cortex_signup.html"


def signup_form_path() -> str:
    """Path of the access-request form used by the login page (see hooks.signup_form_template)."""
    return SIGNUP_TEMPLATE


def boot_session(bootinfo) -> None:
    """Read-only: tell the Desk that a company owner still has an unfinished setup (no database write)."""
    if not frappe or frappe.session.user in ("Administrator", "Guest"):
        return
    try:
        from cortex_rental.services import onboarding

        if onboarding.needs_onboarding(frappe.session.user):
            bootinfo.cortex_onboarding = {"route": ONBOARDING_ROUTE.replace("/app/", "")}
    except Exception:
        # Never block the Desk because of onboarding bookkeeping.
        frappe.log_error(title="Cortex onboarding boot flag failed")
