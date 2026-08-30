try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexAgentRun(Document):
    """
    One logical agent run (e.g. one Onyx conversation turn), grouping
    every Cortex Agent Tool Call made under the same request_id.
    Only services/agent_telemetry.py should write to this DocType
    (via ignore_permissions, the same pattern as Audit Event) — it
    updates status/tool_call_count/last_seen_at as tool calls come in.
    Deletion is blocked; this is not exposed as a general-purpose
    editable record.
    """

    def on_trash(self):
        if frappe:
            frappe.throw("Cortex Agent Run records cannot be deleted.", frappe.PermissionError)
        raise PermissionError("Cortex Agent Run records cannot be deleted.")
