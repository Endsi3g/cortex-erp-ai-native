"""Action proposée par l'assistant IA : créée et décidée seulement par le serveur (services/ai/actions.py)."""

try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    frappe = None

    class Document:
        pass


class CortexAIAction(Document):
    def validate(self):
        if not (self.flags.from_ai_actions or frappe.session.user == "Administrator"):
            frappe.throw("Les actions de l'assistant sont créées depuis la conversation.", frappe.PermissionError)

    def on_trash(self):
        if frappe.flags.get("dev_cleanup"):
            return
        frappe.throw("Une action de l'assistant ne se supprime pas : elle reste au journal.", frappe.PermissionError)
