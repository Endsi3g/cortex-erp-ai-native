try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class CortexSubscriptionItem(Document):
    """Option payante d'un abonnement Cortex (module ou niveau d'IA), avec son prix Stripe."""
