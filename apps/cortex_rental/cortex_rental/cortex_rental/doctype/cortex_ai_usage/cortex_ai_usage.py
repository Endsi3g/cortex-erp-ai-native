"""Un appel au modèle : jetons et coût, par société. Écrit seulement par la passerelle, jamais modifié."""

try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    frappe = None

    class Document:
        pass


class CortexAIUsage(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("L'usage de l'IA ne se modifie pas.")
        if not (self.flags.from_gateway or frappe.session.user == "Administrator"):
            frappe.throw("L'usage est enregistré par la passerelle IA.", frappe.PermissionError)

    def on_trash(self):
        if frappe.flags.get("dev_cleanup"):
            return
        frappe.throw("L'usage de l'IA ne se supprime pas.", frappe.PermissionError)
