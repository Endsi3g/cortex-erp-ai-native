"""Landing page of the emailed verification link: /cortex-verify?token=..."""

import frappe

from cortex_rental.services import access_requests

no_cache = True
sitemap = 0


def get_context(context):
    context.no_breadcrumbs = True
    context.title = "Vérification du courriel"
    token = (frappe.form_dict.get("token") or "")[:200]
    context.result = access_requests.verify_token(token)
    return context
