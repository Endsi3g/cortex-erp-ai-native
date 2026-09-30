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
                    "Une pièce justificative doit contenir un fichier ou un extrait de texte.",
                    frappe.ValidationError,
                )
            else:
                raise ValueError("Une pièce justificative doit contenir un fichier ou un extrait de texte.")
