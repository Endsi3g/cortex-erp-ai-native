try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexChatContextSnapshot(Document):
    """
    An immutable record of what a chat turn was allowed to see — the
    *resolved* (server-validated) context, not whatever the client
    originally sent. Written only by services/chat_context.py.
    """

    def on_trash(self):
        if frappe:
            frappe.throw("Cortex Chat Context Snapshot records cannot be deleted.", frappe.PermissionError)
        raise PermissionError("Cortex Chat Context Snapshot records cannot be deleted.")
