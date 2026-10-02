import frappe
from frappe import _
from frappe.model.document import Document

# Une facture émise est un instantané : seuls les paiements (et les notes) la font évoluer.
FROZEN_FIELDS = (
    "company",
    "customer",
    "rental_transaction",
    "invoice_type",
    "issue_date",
    "subtotal",
    "tps_amount",
    "tvq_amount",
    "tax_amount",
    "total",
    "amount_paid",
    "balance",
    "status",
)


class CortexRentalInvoice(Document):
    def validate(self):
        if self.flags.from_billing or self.is_new():
            if self.is_new() and not self.flags.from_billing and frappe.session.user != "Administrator":
                frappe.throw(
                    _("Les factures sont émises par Cortex à la réservation et à la clôture."), frappe.PermissionError
                )
            return
        before = self.get_doc_before_save()
        if before and any(before.get(field) != self.get(field) for field in FROZEN_FIELDS):
            frappe.throw(
                _("Une facture émise ne peut plus être modifiée : enregistrez un paiement ou un remboursement.")
            )

    def on_trash(self):
        if frappe.flags.get("dev_cleanup"):
            return
        frappe.throw(_("Une facture ne se supprime pas."), frappe.PermissionError)
