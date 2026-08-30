try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class RentalPricingRule(Document):
    """
    Versioned rental pricing rules (e.g. 7 calendar days = 3 billable days).
    """

    pass
