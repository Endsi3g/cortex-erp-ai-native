"""Portail de demandes : /demande/<identifiant>. Aucune connexion; seul un portail activé par la société répond."""

import frappe
from frappe.rate_limiter import rate_limit

from cortex_rental.services import brand, client_portal

no_cache = True
sitemap = 0


@rate_limit(limit=300, seconds=60 * 60)
def _info(slug: str):
    return client_portal.company_for_slug(slug)


def get_context(context):
    context.no_breadcrumbs = True
    context.no_cache = 1
    slug = (frappe.form_dict.get("slug") or "")[:60].lower()
    info = _info(slug)
    context.slug = slug if info else ""
    context.info = info or {}
    context.state = "ok" if info else "closed"
    context.cortex_site = brand.cortex_site_url()
    context.title = f"Demande de location — {info['name']}" if info else "Demande de location"
    return context
