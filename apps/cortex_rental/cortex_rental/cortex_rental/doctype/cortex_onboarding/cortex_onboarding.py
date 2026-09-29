"""Progress of the guided setup of one company (see api/v1/onboarding.py)."""

try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class CortexOnboarding(Document):
    pass
