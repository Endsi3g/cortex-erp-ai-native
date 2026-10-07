try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    frappe = None

    class Document:
        pass


class CortexSubscriptionSettings(Document):
    def validate(self):
        from cortex_rental.services import subscriptions

        for message in subscriptions.settings_problems(self.as_dict() if hasattr(self, "as_dict") else {}):
            frappe.throw(message)
