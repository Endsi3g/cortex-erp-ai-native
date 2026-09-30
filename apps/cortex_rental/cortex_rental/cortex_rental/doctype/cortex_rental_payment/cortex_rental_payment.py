import frappe
from frappe import _
from frappe.model.document import Document

from cortex_rental.services import billing, ledger
from cortex_rental.services.audit import AuditService


class CortexRentalPayment(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw(_("Un paiement enregistré ne se modifie pas : enregistrez un remboursement."))
        billing.validate_payment(self)

    def after_insert(self):
        billing.refresh_invoice(self.invoice)
        ledger.post_payment(self)
        AuditService.record_mutation(
            company=self.company,
            action="cortex.payment.recorded",
            entity_type="Cortex Rental Payment",
            entity_id=self.name,
            after_state={"invoice": self.invoice, "kind": self.kind, "amount": self.amount, "method": self.method},
        )

    def on_trash(self):
        if frappe.flags.get("dev_cleanup"):
            return
        frappe.throw(_("Un paiement ne se supprime pas."), frappe.PermissionError)
