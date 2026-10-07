import frappe
from frappe import _
from frappe.model.document import Document


class CortexFinanceSettings(Document):
    def validate(self):
        self.validate_portal()
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

    def validate_portal(self):
        """Portail de demandes : identifiant propre à la société (adresse publique), jamais en double."""
        from cortex_rental.services.client_portal import SLUG_RE

        slug = (self.portal_slug or "").strip().lower()
        self.portal_slug = slug
        if self.portal_requests_enabled and not slug:
            frappe.throw(_("Indiquez l'identifiant du portail pour l'activer."))
        if slug:
            if not SLUG_RE.match(slug):
                frappe.throw(_("L'identifiant du portail compte 3 à 40 caractères : minuscules, chiffres et tirets."))
            other = frappe.db.get_value(
                "Cortex Finance Settings", {"portal_slug": slug, "name": ["!=", self.name or ""]}, "name"
            )
            if other:
                frappe.throw(_("Cet identifiant de portail est déjà utilisé : choisissez-en un autre."))
        if self.cheque_payable_to and len(self.cheque_payable_to) > 140:
            frappe.throw(_("Le nom pour le chèque est trop long."))
