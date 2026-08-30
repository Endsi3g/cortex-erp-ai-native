try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexExtractionRun(Document):
    """
    Append-only record of one structured-extraction attempt (PRD §2.1:
    "extraction JSON structurée → validation de schéma → Evidence
    Reference → objets métier Cortex"). Written exclusively via
    services/extraction.record_extraction_run(), which performs the
    schema validation and confidence-threshold check that populate
    validation_status/review_required — never edited directly.
    """

    def before_save(self):
        if hasattr(self, "is_new") and not self.is_new():
            if frappe:
                frappe.throw("Cortex Extraction Run records are immutable.", frappe.PermissionError)
            raise PermissionError("Cortex Extraction Run records are immutable.")

    def on_trash(self):
        if frappe:
            frappe.throw("Cortex Extraction Run records cannot be deleted.", frappe.PermissionError)
        raise PermissionError("Cortex Extraction Run records cannot be deleted.")
