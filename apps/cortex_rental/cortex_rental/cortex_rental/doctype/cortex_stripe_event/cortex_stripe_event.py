try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class CortexStripeEvent(Document):
    """Événement Stripe déjà traité : un rejeu du même événement est ignoré (idempotence)."""
