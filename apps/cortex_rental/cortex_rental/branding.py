"""Apply the Cortex brand to the site settings that Frappe/ERPNext ship with their own name and logo.

Idempotent and non-destructive: a value is replaced only when it is empty or still one of the
framework defaults, so a customised Website Settings / Navbar Settings is left alone.
"""

try:
    import frappe
except ImportError:  # unit tests without a bench
    frappe = None

BRAND_NAME = "Cortex"
LOGO = "/assets/cortex_rental/images/cortex-logo.svg"
FAVICON = "/assets/cortex_rental/images/cortex-favicon.svg"
DEFAULT_NAMES = {"", "Frappe", "ERPNext", "Frappe Framework"}
MIN_PASSWORD_SCORE = 3


def _is_default_logo(value):
    return not value or "/assets/frappe/" in value or "/assets/erpnext/" in value


def apply_branding():
    """Name, logo and favicon on Website, Navbar and System Settings; stricter password policy."""
    changed = []

    def set_single(doctype, field, value, should_replace):
        current = frappe.db.get_single_value(doctype, field)
        if should_replace(current):
            frappe.db.set_single_value(doctype, field, value)
            changed.append(f"{doctype}.{field}")

    set_single("Website Settings", "app_name", BRAND_NAME, lambda v: (v or "") in DEFAULT_NAMES)
    set_single("Website Settings", "app_logo", LOGO, _is_default_logo)
    set_single("Website Settings", "favicon", FAVICON, lambda v: not v)
    set_single("Navbar Settings", "app_logo", LOGO, _is_default_logo)
    set_single("System Settings", "app_name", BRAND_NAME, lambda v: (v or "") in DEFAULT_NAMES)

    # Enterprise default: a zxcvbn score of at least 3, never weakened by this function.
    frappe.db.set_single_value("System Settings", "enable_password_policy", 1)
    score = frappe.db.get_single_value("System Settings", "minimum_password_score")
    if int(score or 0) < MIN_PASSWORD_SCORE:
        frappe.db.set_single_value("System Settings", "minimum_password_score", MIN_PASSWORD_SCORE)
        changed.append("System Settings.minimum_password_score")
    return changed
