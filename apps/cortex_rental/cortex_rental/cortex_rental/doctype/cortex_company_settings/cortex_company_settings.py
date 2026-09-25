try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    frappe = None

    class Document:
        pass


class CortexCompanySettings(Document):
    """Per-company billing settings: advance share, equipment guarantee, tax template, damage/loss items."""

    def validate(self):
        pct = float(self.advance_percentage or 0)
        if pct < 0 or pct > 100:
            frappe.throw("Le pourcentage d’acompte doit être entre 0 et 100.", frappe.ValidationError)
