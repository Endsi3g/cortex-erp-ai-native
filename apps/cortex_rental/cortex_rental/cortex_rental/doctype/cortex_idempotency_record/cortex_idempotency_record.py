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
                    "Les enregistrements d'idempotence sont immuables et ne peuvent pas être modifiés.",
                    frappe.PermissionError,
                )
            raise PermissionError("Les enregistrements d'idempotence sont immuables.")

    def on_trash(self):
        if frappe:
            frappe.throw("Les enregistrements d'idempotence ne peuvent pas être supprimés.", frappe.PermissionError)
        raise PermissionError("Les enregistrements d'idempotence ne peuvent pas être supprimés.")
