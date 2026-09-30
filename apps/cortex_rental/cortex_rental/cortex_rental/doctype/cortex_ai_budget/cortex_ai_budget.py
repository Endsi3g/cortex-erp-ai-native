try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class CortexAIBudget(Document):
    pass
