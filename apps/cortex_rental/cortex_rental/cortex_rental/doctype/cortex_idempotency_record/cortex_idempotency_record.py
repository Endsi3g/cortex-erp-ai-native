try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexIdempotencyRecord(Document):
    """
    Immutable dedup record for a (Company, scope, Idempotency-Key) tuple.
    Never updated after creation — a retried call reads the recorded
    response instead of mutating this record. See services/idempotency.py.
    """

    def before_save(self):
        if hasattr(self, "is_new") and not self.is_new():
            if frappe:
                frappe.throw(
                    "Idempotency records are immutable and cannot be modified.",
                    frappe.PermissionError,
                )
            raise PermissionError("Idempotency records are immutable.")

    def on_trash(self):
        if frappe:
            frappe.throw("Idempotency records cannot be deleted.", frappe.PermissionError)
        raise PermissionError("Idempotency records cannot be deleted.")
