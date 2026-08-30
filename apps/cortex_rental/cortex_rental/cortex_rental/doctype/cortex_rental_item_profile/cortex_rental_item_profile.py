try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexRentalItemProfile(Document):
    """
    Rental specific profile attached to standard ERPNext Item.
    Maintains daily rates, replacement value, prep hours, and required kit accessories.
    """

    pass
