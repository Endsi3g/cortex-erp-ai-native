try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class CortexSubscription(Document):
    """État de l'abonnement Cortex d'une société. Écrit seulement par le webhook Stripe signé (jamais par le navigateur)."""
