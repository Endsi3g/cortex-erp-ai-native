"""Hook targets for the login experience: signup form template and the onboarding flag."""

try:
    import frappe
except ImportError:
    frappe = None

# Pour l'instant l'arrivée se fait sur l'espace Cortex Rental; l'Accueil IA (`cortex-home`) reste ouvert à la demande.
HOME_ROUTE = "cortex-rental"
SIGNUP_TEMPLATE = "cortex_rental/templates/includes/cortex_signup.html"


def signup_form_path() -> str:
    """Path of the access-request form used by the login page (see hooks.signup_form_template)."""
    return SIGNUP_TEMPLATE


def french_for_guests() -> None:
    """Cortex ships in French only: a visitor who is not signed in and chose no language gets French pages.

    Signed-in people keep the language of their profile (French unless they picked another one). An explicit `_lang`
    parameter or `preferred_language` cookie still wins.
    """
    if not frappe or frappe.session.user != "Guest":
        return
    request = getattr(frappe.local, "request", None)
    if request is None:
        return
    if request.args.get("_lang") or request.cookies.get("preferred_language"):
        return
    frappe.local.lang = "fr"


def _company_identity() -> dict:
    """Name and logo of the person's company for the AI home (read-only, both may be empty)."""
    identity = {"company": "", "company_logo": ""}
    try:
        from cortex_rental.permissions.agent_scopes import get_company_context

        company = get_company_context()
    except Exception:
        company = frappe.defaults.get_user_default("Company") or ""
    if company:
        identity["company"] = company
        identity["company_logo"] = frappe.db.get_value("Company", company, "company_logo") or ""
    return identity


def boot_session(bootinfo) -> None:
    """Read-only: tell the Desk where people land after sign-in and whether the owner's setup is unfinished.

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
    home.update(_company_identity())
    bootinfo.cortex_home = home
