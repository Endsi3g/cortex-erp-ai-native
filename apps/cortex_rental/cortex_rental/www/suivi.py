"""Suivi d'une demande : /suivi/<jeton>. Le jeton est la seule clé; la page ne montre rien de personnel."""

import frappe
from frappe.rate_limiter import rate_limit

from cortex_rental.services import brand, client_portal

no_cache = True
sitemap = 0


@rate_limit(limit=300, seconds=60 * 60)
def _track(token: str):
    return client_portal.track(token)


def get_context(context):
    context.no_breadcrumbs = True
    context.no_cache = 1
    view = _track((frappe.form_dict.get("token") or "")[:100])
    context.view = view
    context.state = view.get("state", "unknown")
    context.cortex_site = brand.cortex_site_url()
    context.title = f"Suivi de votre demande — {view['company']}" if view.get("company") else "Suivi de votre demande"
    context.fmt_day = lambda value: frappe.utils.format_datetime(value[:10], "d MMM yyyy") if value else ""
    return context
