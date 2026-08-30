try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    class Document:
        pass
    frappe = None


class CortexRentalTransactionItem(Document):
    pass
