import frappe
from frappe import _
from frappe.model.document import Document


class CortexFinanceSettings(Document):
    def validate(self):
        for field, label in (("tps_rate", "TPS"), ("tvq_rate", "TVQ")):
            if not 0 <= (self.get(field) or 0) <= 30:
                frappe.throw(_("Le taux de {0} doit être compris entre 0 et 30 %.").format(label))
        if not 0 <= (self.deposit_percent or 0) <= 100:
            frappe.throw(_("L'acompte doit être compris entre 0 et 100 %."))
        if not 0 <= (self.late_fee_percent or 0) <= 1000:
            frappe.throw(_("Les frais de retard doivent être compris entre 0 et 1000 % du tarif journalier."))
        if (
            (self.late_fee_grace_minutes or 0) < 0
            or (self.late_fee_cap_days or 0) < 0
            or (self.invoice_due_days or 0) < 0
        ):
            frappe.throw(_("Les délais et plafonds ne peuvent pas être négatifs."))
