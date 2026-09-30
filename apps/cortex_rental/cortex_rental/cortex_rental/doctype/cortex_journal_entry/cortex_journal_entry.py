import frappe
from frappe import _
from frappe.model.document import Document

TOLERANCE = 0.005


class CortexJournalEntry(Document):
    """Écriture comptable à partie double : toujours équilibrée, jamais modifiée ni supprimée (on passe une écriture inverse)."""

    def validate(self):
        if not self.is_new():
            frappe.throw(_("Une écriture comptable ne se modifie pas : on passe une écriture inverse."))
        if not (self.flags.from_ledger or frappe.session.user == "Administrator"):
            frappe.throw(
                _("Les écritures sont générées par Cortex à chaque facture et paiement."), frappe.PermissionError
            )
        self.total_debit = round(sum(float(line.debit or 0) for line in self.lines), 2)
        self.total_credit = round(sum(float(line.credit or 0) for line in self.lines), 2)
        if abs(self.total_debit - self.total_credit) > TOLERANCE:
            frappe.throw(
                _("L'écriture n'est pas équilibrée : débits {0}, crédits {1}.").format(
                    self.total_debit, self.total_credit
                )
            )
        if self.total_debit <= 0:
            frappe.throw(_("Une écriture doit avoir un montant."))
        for line in self.lines:
            if (line.debit or 0) < 0 or (line.credit or 0) < 0 or ((line.debit or 0) and (line.credit or 0)):
                frappe.throw(_("Chaque ligne est soit un débit, soit un crédit, jamais négatif."))

    def on_trash(self):
        if frappe.flags.get("dev_cleanup"):
            return
        frappe.throw(_("Une écriture comptable ne se supprime pas."), frappe.PermissionError)
