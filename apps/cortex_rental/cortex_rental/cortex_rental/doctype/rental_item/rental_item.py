try:
    from frappe.model.document import Document
except ImportError:
    class Document:
        pass

class RentalItem(Document):
    """
    Rental catalog equipment item, specifications and rates.
    """
    pass
