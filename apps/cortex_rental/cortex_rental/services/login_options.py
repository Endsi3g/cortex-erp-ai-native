"""What the sign-in screen can offer a visitor: social providers, email link, access requests.

Mirrors the checks of `frappe.www.login.get_context` (a provider is listed only when it is enabled and has a
client id, a secret and OAuth keys) but returns plain data for the Vue client instead of HTML.
"""

from typing import Any, Dict, List
from urllib.parse import urlparse

try:
    import frappe
    from frappe.utils import cint
except ImportError:
    frappe = None

DEFAULT_LANDING = "/cortex"


def safe_redirect(target: str, base: str = DEFAULT_LANDING) -> str:
    """Only same-site absolute paths survive: `//host`, `https://host` and backslash tricks fall back to the app."""
    value = (target or "").strip()
    if not value.startswith("/") or value.startswith("//") or "\\" in value or urlparse(value).netloc:
        return base
    return value


def login_options(redirect_to: str = "") -> Dict[str, Any]:
    from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
    from frappe.utils.password import get_decrypted_password

    from cortex_rental.services.access_requests import signup_enabled

    target = safe_redirect(redirect_to)
    providers: List[Dict[str, str]] = []
    rows = frappe.get_all(
        "Social Login Key",
        filters={"enable_social_login": 1},
        fields=["name", "client_id", "base_url", "provider_name", "icon"],
        order_by="name",
    )
    for row in rows:
        secret = get_decrypted_password("Social Login Key", row.name, "client_secret", raise_exception=False)
        if not secret or not (row.client_id and row.base_url and get_oauth_keys(row.name)):
            continue
        providers.append(
            {
                "name": row.name,
                "label": row.provider_name,
                "url": get_oauth2_authorize_url(row.name, target),
                "icon": row.icon or "",
            }
        )
    return {
        "providers": providers,
        "email_link": bool(cint(frappe.get_system_settings("login_with_email_link"))),
        "password_login": not cint(frappe.get_system_settings("disable_user_pass_login")),
        "signup_enabled": bool(signup_enabled()),
        "redirect_to": target,
    }
