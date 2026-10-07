"""Abonnement Cortex d'une société : état, achat (Stripe Checkout), gestion et webhook signé.

Seul le propriétaire (ou un administrateur du site) voit et gère l'abonnement. Les droits ne sont jamais écrits par le
navigateur : seul le webhook signé de Stripe modifie l'état (services/subscriptions.py, ADR-010)."""

try:
    import frappe
    from frappe.rate_limiter import rate_limit
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services import administration, defense, subscriptions
from cortex_rental.services.payments import PaymentError

WEBHOOK_MAX_BYTES = 1024 * 1024


def _require_owner_company() -> str:
    require_human_staff_role()
    if not administration.can_manage_team(frappe.session.user):
        frappe.throw("Seul le propriétaire de la société gère l'abonnement.", frappe.PermissionError)
    return get_company_context()


if frappe:

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_subscription():
        """État de l'abonnement, droits et options offertes (aucun secret, aucun identifiant Stripe)."""
        return {"data": subscriptions.public_status(_require_owner_company())}

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("subscription_checkout", 10)
    def start_checkout(options: str = ""):
        """Crée la session de paiement de l'abonnement (plan de base + options choisies) et renvoie son adresse."""
        company = _require_owner_company()
        chosen = defense.json_object({"options": frappe.parse_json(options or "[]")}, "Les options")["options"]
        if not isinstance(chosen, list) or not all(isinstance(c, dict) for c in chosen):
            frappe.throw("Les options doivent être une liste.", frappe.ValidationError)
        try:
            return {"data": subscriptions.start_checkout(company, chosen)}
        except PaymentError as exc:
            frappe.throw(str(exc), frappe.ValidationError)

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("subscription_portal", 10)
    def open_portal():
        """Ouvre le portail Stripe de gestion de l'abonnement (carte, factures, changement, annulation)."""
        company = _require_owner_company()
        try:
            return {"data": subscriptions.open_portal(company)}
        except PaymentError as exc:
            frappe.throw(str(exc), frappe.ValidationError)

    @frappe.whitelist(allow_guest=True, methods=["POST"])
    @defense.safe_input
    @rate_limit(limit=600, seconds=60)
    def subscription_webhook():
        """Stripe (compte de la plateforme) : état de l'abonnement. Signature vérifiée, événement traité une fois."""
        frappe.local.response["http_status_code"] = 200
        if (frappe.request.content_length or 0) > WEBHOOK_MAX_BYTES:
            frappe.local.response["http_status_code"] = 413
            return {"ok": False, "code": "too_large"}
        result = subscriptions.handle_event(
            frappe.request.get_data(), frappe.get_request_header("Stripe-Signature") or ""
        )
        if not result.get("ok"):
            frappe.local.response["http_status_code"] = 400
        return result
