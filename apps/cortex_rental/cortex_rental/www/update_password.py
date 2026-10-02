"""Context for the password page (set after an invitation, reset after « Forgot password »)."""

import frappe
from frappe import _

no_cache = 1


def get_context(context):
    frappe.local.lang = "fr" if frappe.form_dict.get("lang") != "en" else frappe.local.lang
    context.no_breadcrumbs = True
    context.parents = [{"name": "me", "title": _("My Account")}]
    context.min_score = int(frappe.get_system_settings("minimum_password_score") or 0)
    context.policy_enabled = bool(frappe.get_system_settings("enable_password_policy"))
    context.logo = "/assets/cortex_rental/images/cortex-logo.svg"
    context.logo_dark = "/assets/cortex_rental/images/cortex-logo-reversed.svg"
