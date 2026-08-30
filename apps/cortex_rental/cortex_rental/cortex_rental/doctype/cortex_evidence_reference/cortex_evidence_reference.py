try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexEvidenceReference(Document):
    """
    A single piece of evidence (uploaded file or text excerpt) backing
    a structured extraction or business decision (PRD §2.1/§8). Neither
    a file nor a text excerpt is trusted as a business fact on its own —
    it only becomes one via a Cortex Extraction Run + human/agent
    business object creation.
    """

    def validate(self):
        if not self.file and not self.text_excerpt:
            if frappe:
                frappe.throw(
                    "A Cortex Evidence Reference must have either a file or a text excerpt.",
                    frappe.ValidationError,
                )
            else:
                raise ValueError("Evidence Reference must have a file or a text excerpt.")
