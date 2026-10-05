"""Lien de devis envoyé à un client : créé seulement par le serveur (services/quote_share.py), jamais modifié à la main."""

try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    frappe = None

    class Document:
        pass


class CortexQuoteShare(Document):
    def validate(self):
        if not (self.flags.from_quote_share or frappe.session.user == "Administrator"):
            frappe.throw("Les liens de devis sont créés depuis la location.", frappe.PermissionError)

    def on_trash(self):
        if frappe.flags.get("dev_cleanup"):
            return
        frappe.throw("Un lien de devis ne se supprime pas : révoquez-le.", frappe.PermissionError)
