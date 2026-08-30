try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexChatMessage(Document):
    """
    One turn (human or agent) in a Cortex Chat Session. Written only by
    services/chat_session.py under ignore_permissions, same pattern as
    Cortex Agent Run/Tool Call — not a general-purpose editable record.
    """

    def on_trash(self):
        if frappe:
            frappe.throw("Cortex Chat Message records cannot be deleted.", frappe.PermissionError)
        raise PermissionError("Cortex Chat Message records cannot be deleted.")
