try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexAgentToolCall(Document):
    """
    Append-only record of a single agent/MCP tool invocation (PRD §7:
    "Tout appel outil est journalisé dans Cortex Agent Tool Call +
    Cortex Audit Event"). Written exclusively by
    services/agent_telemetry.py; never carries raw request/response
    payloads or documents, only the tool name, scope, outcome and an
    error message where relevant.
    """

    def before_save(self):
        if hasattr(self, "is_new") and not self.is_new():
            if frappe:
                frappe.throw("Agent Tool Call records are immutable.", frappe.PermissionError)
            raise PermissionError("Agent Tool Call records are immutable.")

    def on_trash(self):
        if frappe:
            frappe.throw("Agent Tool Call records cannot be deleted.", frappe.PermissionError)
        raise PermissionError("Agent Tool Call records cannot be deleted.")
