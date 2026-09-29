"""Site-wide policy for access requests (self-service sign-up of a new company)."""

try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class CortexAccessSettings(Document):
    pass
