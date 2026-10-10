"""Hook targets for the login experience: signup form template and the onboarding flag."""

try:
    import frappe
except ImportError:
    frappe = None

# Première page après la connexion : l'Assistant IA (décision de Kael, 2026-10-07). Les personnes dont aucun rôle ne
# donne accès à cette Page retombent sur l'espace Cortex Rental plutôt que sur une erreur de droits.
HOME_ROUTE = "cortex-home"
FALLBACK_HOME_ROUTE = "cortex-rental"
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


def home_route_for(user: str) -> str:
    """Route d'arrivée de la personne : l'Assistant IA si l'un de ses rôles ouvre la Page, sinon l'espace Cortex Rental."""
    try:
        allowed = set(frappe.get_all("Has Role", filters={"parenttype": "Page", "parent": HOME_ROUTE}, pluck="role"))
        if allowed and allowed.intersection(frappe.get_roles(user)):
            return HOME_ROUTE
    except Exception:
        pass
    return FALLBACK_HOME_ROUTE


def boot_session(bootinfo) -> None:
    """Read-only: tell the Desk where people land after sign-in and whether the owner's setup is unfinished.

    `public/js/cortex_desk.js` sends a signed-in person who lands on the bare `/app` to that Page. The hook never
    writes to the database and never blocks the Desk.
    """
    if not frappe or frappe.session.user == "Guest":
        return
    home = {"route": home_route_for(frappe.session.user), "setup_pending": False}
    if frappe.session.user != "Administrator":
        try:
            from cortex_rental.services import onboarding

            home["setup_pending"] = bool(onboarding.needs_onboarding(frappe.session.user))
            home["setup_required_missing"] = bool(
                home["setup_pending"] and onboarding.has_required_missing(frappe.session.user)
            )
        except Exception:
            # Never block the Desk because of onboarding bookkeeping.
            frappe.log_error(title="Cortex onboarding boot flag failed")
    home.update(_company_identity())
    bootinfo.cortex_home = home
    try:
        from cortex_rental.services import sector_templates

        bootinfo.cortex_categories = sector_templates.categories()
    except Exception:
        # Sans cette liste, l'interface retombe sur sa liste d'origine : jamais bloquer le Desk.
        frappe.log_error(title="Cortex categories boot failed")
    try:
        from cortex_rental.services import analytics

        config = analytics.boot_config(frappe.session.user, home.get("company") or "")
        if config:
            bootinfo.cortex_analytics = config
    except Exception:
        # La mesure d'usage ne doit jamais bloquer le Desk.
        frappe.log_error(title="Cortex analytics boot config failed")
