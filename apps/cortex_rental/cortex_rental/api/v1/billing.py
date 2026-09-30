"""Facturation : enregistrement des paiements (toute écriture passe par le serveur, avec les droits de l'utilisateur)."""

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services import billing
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency

if frappe:

    @frappe.whitelist(methods=["POST"])
    def record_payment(
        invoice: str,
        amount: float,
        method: str = "Card",
        paid_on: str = None,
        reference: str = None,
        kind: str = "Payment",
        notes: str = None,
    ):
        require_human_staff_role()
        company = get_company_context()
        if frappe.db.get_value("Cortex Rental Invoice", invoice, "company") != company:
            frappe.throw("Facture introuvable.", frappe.PermissionError)
        if not frappe.has_permission("Cortex Rental Payment", "create"):
            frappe.throw("Vous n'avez pas le droit d'enregistrer un paiement.", frappe.PermissionError)

        def create():
            doc = billing.record_payment(
                invoice=invoice,
                amount=float(amount),
                method=method,
                paid_on=paid_on,
                reference=reference,
                kind=kind,
                notes=notes,
            )
            return doc.name

        name = with_idempotency(
            company=company,
            scope="billing.record_payment",
            idempotency_key=get_idempotency_key_header(),
            payload={"invoice": invoice, "amount": amount, "method": method, "kind": kind, "reference": reference},
            handler=create,
        )
        balance = frappe.db.get_value(
            "Cortex Rental Invoice", invoice, ["balance", "status", "amount_paid"], as_dict=True
        )
        return {"payment": name, "invoice": invoice, **balance}
