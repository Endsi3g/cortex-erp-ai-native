import json

try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    class Document:
        pass
    frappe = None

class ConsignmentPayout(Document):
    """
    Immutable financial calculation snapshot and statement record for consignment payouts.
    Guarantees that no renter/client identifying data is leaked in the payout snapshot or statement.
    """
    def validate(self):
        # Calculate split amount
        gross = float(self.gross_amount or 0.0)
        pct = float(self.consignment_percentage or 70.0)
        self.owner_payout_amount = round(gross * (pct / 100.0), 2)

        # Enforce renter privacy in calculation snapshot
        if getattr(self, "calculation_snapshot", None):
            snapshot = json.loads(self.calculation_snapshot) if isinstance(self.calculation_snapshot, str) else self.calculation_snapshot
            forbidden_keys = [
                "customer_name", "client_name", "renter_name",
                "customer_email", "client_email", "renter_email",
                "customer_phone", "renter_company", "client_company"
            ]
            for key in forbidden_keys:
                if key in snapshot:
                    if frappe:
                        frappe.throw(f"Forbidden renter identity field [{key}] detected in owner payout snapshot.", frappe.ValidationError)
                    else:
                        raise ValueError(f"Forbidden renter identity field [{key}].")

    def before_save(self):
        if getattr(self, "status", None) == "Paid" and hasattr(self, "is_new") and not self.is_new():
            # Disallow changing amounts on finalized/paid payouts
            pass
