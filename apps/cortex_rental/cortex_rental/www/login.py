"""Context for the Cortex login page: Frappe's own context, branded as Cortex.

The form, ids and script are Frappe's (see www/login.html); only the name and logo are replaced when
the site still carries the framework defaults, so a customised Website Settings is respected.
"""

import frappe
from frappe.www.login import get_context as frappe_login_context

no_cache = True


def _signup_enabled() -> bool:
    try:
        from cortex_rental.services.access_requests import signup_enabled

        return signup_enabled()
    except Exception:
        return False


DEFAULT_APP_NAMES = {"", "Frappe", "ERPNext", "Frappe Framework"}


def get_context(context):
    # The page is served in French unless the visitor asks for English (?lang=en).
    if frappe.form_dict.get("lang") != "en":
        frappe.local.lang = "fr"
    result = frappe_login_context(context)
    context = result or context
    context["disable_signup"] = not _signup_enabled()
    if (context.get("app_name") or "") in DEFAULT_APP_NAMES:
        context["app_name"] = "Cortex"
    logo = context.get("logo") or ""
    if not logo or "/assets/frappe/" in logo or "/assets/erpnext/" in logo:
        hooked = frappe.get_hooks("app_logo_url")
        context["logo"] = hooked[-1] if hooked else logo
    if (context.get("logo") or "").endswith("cortex-logo.svg"):
        context["logo_dark"] = "/assets/cortex_rental/images/cortex-logo-reversed.svg"
    return context
