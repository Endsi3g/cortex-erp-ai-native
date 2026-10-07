"""Page publique d'un devis : /devis/<jeton>. Aucune connexion ; le jeton est la seule clé (voir services/quote_share.py)."""

import frappe
from frappe.rate_limiter import rate_limit

from cortex_rental.services import brand, quote_share

no_cache = True
sitemap = 0


@rate_limit(limit=300, seconds=60 * 60)
def _view(token: str):
    return quote_share.public_view(token)


def get_context(context):
    context.no_breadcrumbs = True
    context.no_cache = 1
    token = (frappe.form_dict.get("token") or "")[:100]
    view = _view(token)
    context.view = view
    context.cortex_site = brand.cortex_site_url()
    context.token = token if view.get("state") == "ok" else ""
    # Le jeton sert aussi à payer l'acompte après l'acceptation (la page ne l'affiche jamais en clair).
    context.view_token = token if view.get("state") in ("ok", "accepted") else ""
    quote = view.get("quote") or {}
    context.quote = quote
    context.title = f"Devis — {quote['company']}" if quote.get("company") else "Devis"
    context.fmt = _money
    context.num = lambda value: f"{float(value or 0):g}".replace(".", ",")
    amounts = [float(line.get("amount") or 0) for line in quote.get("lines") or []]
    biggest = max(amounts) if amounts else 0
    total = float(quote.get("total") or 0)
    context.share = lambda amount: round(float(amount or 0) / biggest * 100) if biggest else 0
    context.pct = lambda amount: round(float(amount or 0) / total * 100, 1) if total else 0
    context.fmt_date = lambda value: frappe.utils.format_datetime(value, "d MMM yyyy, HH:mm") if value else ""
    context.fmt_day = lambda value: frappe.utils.format_datetime(value[:10], "d MMM yyyy") if value else ""
    return context


def _money(amount) -> str:
    """Montant à la québécoise : « 2 127,00 $ »."""
    text = f"{float(amount or 0):,.2f}".replace(",", "\u00a0").replace(".", ",")
    return f"{text}\u00a0$"
