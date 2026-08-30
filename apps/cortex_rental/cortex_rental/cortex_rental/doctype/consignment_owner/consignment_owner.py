try:
    from frappe.model.document import Document
except ImportError:
    class Document:
        pass

class ConsignmentOwner(Document):
    """
    Third-party consignment equipment owner.
    """
    pass
