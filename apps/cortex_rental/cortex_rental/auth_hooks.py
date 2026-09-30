"""Hook targets for the login experience: signup form template and the onboarding flag."""

try:
    import frappe
except ImportError:
    frappe = None

HOME_ROUTE = "cortex-home"
SIGNUP_TEMPLATE = "cortex_rental/templates/includes/cortex_signup.html"


def signup_form_path() -> str:
    """Path of the access-request form used by the login page (see hooks.signup_form_template)."""
    return SIGNUP_TEMPLATE


def boot_session(bootinfo) -> None:
    """Read-only: tell the Desk where the AI-first home is and whether the owner's setup is unfinished.

    `public/js/cortex_desk.js` sends a signed-in person who lands on the bare `/app` to that Page. The hook never
    writes to the database and never blocks the Desk.
    """
    if not frappe or frappe.session.user == "Guest":
        return
    home = {"route": HOME_ROUTE, "setup_pending": False}
    if frappe.session.user != "Administrator":
        try:
            from cortex_rental.services import onboarding

            home["setup_pending"] = bool(onboarding.needs_onboarding(frappe.session.user))
        except Exception:
            # Never block the Desk because of onboarding bookkeeping.
            frappe.log_error(title="Cortex onboarding boot flag failed")
    bootinfo.cortex_home = home
