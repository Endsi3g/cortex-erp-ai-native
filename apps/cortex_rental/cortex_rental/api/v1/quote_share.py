"""Partage d'un devis avec le client.

- Côté équipe (connecté, permissions vérifiées) : créer un lien (à copier ou envoyé par courriel), lister, révoquer.
- Côté client (sans compte, limité par IP) : consulter l'instantané du devis et répondre (accepter, refuser, demander
  une modification). Le client ne peut rien d'autre : aucune écriture sur la location, aucune réservation.
Règles : services/quote_share.py et docs/adr/ADR-007-portail-de-devis.md.
"""

try:
    import frappe
    from frappe.rate_limiter import rate_limit
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services import quote_share

if frappe:
    # ---------------------------------------------------------------- équipe
    @frappe.whitelist(methods=["POST"])
    def create_share(
        rental_id: str,
        channel: str = "Link",
        recipient_email: str = "",
        recipient_name: str = "",
        message: str = "",
        valid_days: int = quote_share.DEFAULT_DAYS,
    ):
        require_human_staff_role()
        company = get_company_context()
        tx = frappe.get_doc("Cortex Rental Transaction", rental_id)
        if tx.company != company:
            frappe.throw("Cette location n'est pas disponible pour la société active.", frappe.PermissionError)
        if not frappe.has_permission("Cortex Rental Transaction", "write", tx):
            frappe.throw("Vous n'avez pas le droit de partager ce devis.", frappe.PermissionError)
        return quote_share.create_share(
            tx,
            channel=channel,
            sender=frappe.session.user,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            message=message,
            valid_days=int(valid_days or quote_share.DEFAULT_DAYS),
        )

    @frappe.whitelist(methods=["GET"])
    def list_shares(rental_id: str):
        require_human_staff_role()
        company = get_company_context()
        if frappe.db.get_value("Cortex Rental Transaction", rental_id, "company") != company:
            frappe.throw("Cette location n'est pas disponible pour la société active.", frappe.PermissionError)
        rows = frappe.get_list(
            quote_share.SHARE,
            filters={"rental_transaction": rental_id},
            fields=[
                "name",
                "status",
                "channel",
                "recipient_name",
                "recipient_email",
                "email_status",
                "expires_at",
                "view_count",
                "reservation_status",
                "reservation_note",
                "payment_status",
                "last_viewed_at",
                "responded_at",
                "responder_name",
                "response_message",
                "creation",
            ],
            order_by="creation desc",
            limit_page_length=20,
        )
        now = frappe.utils.now_datetime()
        out = []
        for row in rows:
            effective = row.status
            if row.status == "Active" and row.expires_at and frappe.utils.get_datetime(row.expires_at) < now:
                effective = "Expired"
            out.append({**dict(row), "effective_status": effective})
        return {"shares": out}

    @frappe.whitelist(methods=["POST"])
    def revoke_share(name: str):
        require_human_staff_role()
        quote_share.revoke(name, get_company_context(), frappe.session.user)
        return {"revoked": name}

    # ---------------------------------------------------------------- client (sans compte)
    @frappe.whitelist(allow_guest=True, methods=["POST"])
    @rate_limit(limit=120, seconds=60 * 60)
    def respond(token: str = "", action: str = "", message: str = "", responder_name: str = ""):
        return quote_share.respond(token, action, message, responder_name)

    @frappe.whitelist(allow_guest=True, methods=["POST"])
    @rate_limit(limit=20, seconds=60 * 60)
    def start_payment(token: str = ""):
        """Client : crée la session de paiement de l'acompte et renvoie l'adresse de la page de paiement."""
        from cortex_rental.services.payments import PaymentError

        try:
            return quote_share.start_payment(token)
        except PaymentError as exc:
            frappe.throw(str(exc), frappe.ValidationError)

    @frappe.whitelist(allow_guest=True, methods=["POST"])
    def stripe_webhook():
        """Stripe : confirmation signée d'un paiement. La signature est vérifiée avec le secret de la société concernée."""
        frappe.local.response["http_status_code"] = 200
        return quote_share.handle_payment_event(
            frappe.request.get_data(), frappe.get_request_header("Stripe-Signature") or ""
        )
