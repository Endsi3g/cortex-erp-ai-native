"""One-time setup of the sign-in options (idempotent): Google and GitHub keys, access settings.

The Social Login Keys are created DISABLED and without credentials: an administrator pastes the OAuth
client id and secret (see docs/auth/LOGIN_AND_ONBOARDING.md) and ticks « Enable Social Login ». The
login page shows a provider button only once it is enabled and complete, so there is never a dead
button. `sign_ups` is « Deny »: Google/GitHub can only sign in people who already have an account.
"""

try:
    import frappe
except ImportError:
    frappe = None

PROVIDERS = ("Google", "GitHub")


def ensure_social_login_keys():
    created = []
    for provider in PROVIDERS:
        name = frappe.scrub(provider)
        if frappe.db.exists("Social Login Key", name):
            continue
        doc = frappe.new_doc("Social Login Key")
        doc.social_login_provider = provider
        doc.get_social_login_provider(provider, initialize=True)
        doc.enable_social_login = 0
        doc.sign_ups = "Deny"
        doc.insert(ignore_permissions=True)
        created.append(name)
    return created


def ensure_access_settings():
    """Materialise the defaults of Cortex Access Settings (manual approval, work emails only)."""
    if frappe.db.exists("DocType", "Cortex Access Settings"):
        frappe.get_single("Cortex Access Settings").save(ignore_permissions=True)


def clear_default_app():
    """Undo the standalone-app default: sign-in lands on the Desk, where `cortex-home` is the first page."""
    if frappe.db.get_single_value("System Settings", "default_app") == "cortex_rental":
        frappe.db.set_single_value("System Settings", "default_app", "")


def run_all():
    from cortex_rental.branding import apply_branding

    apply_branding()
    ensure_social_login_keys()
    ensure_access_settings()
