import json
from typing import Any, Optional

try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    class Document:
        pass
    frappe = None

from cortex_rental.services.pricing import PricingService
from cortex_rental.services.transaction_state import TransactionStateService
from cortex_rental.services.audit import AuditService


class CortexRentalTransaction(Document):
    """
    Primary Transaction Hub for Cortex Rental Operations.
    Manages rental lifecycle Quote -> Reservation -> Contract -> Checked Out -> Returned -> Closed.
    """
    def validate(self):
        # 1. Compute duration and billable days
        if self.starts_at and self.ends_at:
            calendar_days, billable_days = PricingService.compute_billable_days(
                self.starts_at, self.ends_at, self.company
            )
            self.calendar_days = calendar_days
            self.billable_days = billable_days

        # 2. Recalculate totals across item lines
        subtotal = 0.0
        if hasattr(self, "items") and self.items:
            for item in self.items:
                item.calendar_days = self.calendar_days
                item.billable_days = self.billable_days
                unit_rate = float(item.rate or 0.0)
                qty = float(item.qty or 1.0)
                discount = float(item.discount_percentage or 0.0)
                item.amount = PricingService.calculate_line_total(
                    unit_rate, qty, self.billable_days, discount
                )
                subtotal += item.amount

        self.subtotal = round(subtotal, 2)
        tax_rate = float(self.tax_rate or 0.0)
        self.tax_amount = round(self.subtotal * (tax_rate / 100.0), 2)
        self.grand_total = round(self.subtotal + self.tax_amount, 2)

    def transition_to(self, new_state: str, reason: Optional[str] = None):
        """
        Transition transaction to a new state with strict policy checks and audit trail.
        """
        is_agent = False
        if frappe:
            roles = frappe.get_roles(frappe.session.user)
            is_agent = "Agent Service Account" in roles or getattr(frappe.flags, "in_agent_context", False)

        allowed, error_msg = TransactionStateService.can_transition(
            current_state=self.rental_state,
            target_state=new_state,
            transaction_doc=self,
            is_agent=is_agent
        )

        if not allowed:
            if frappe:
                frappe.throw(error_msg, frappe.PermissionError)
            else:
                raise PermissionError(error_msg)

        before_state = {"rental_state": self.rental_state}
        self.rental_state = new_state
        self.save()

        # Synchronize with ERPNext documents
        TransactionStateService.sync_with_erpnext(self)

        # Append-only audit record
        AuditService.record_mutation(
            company=self.company,
            action=f"cortex.rental_transaction.transition_to_{new_state.lower()}",
            entity_type="Cortex Rental Transaction",
            entity_id=self.name if hasattr(self, "name") else "new",
            before_state=before_state,
            after_state={"rental_state": new_state, "reason": reason}
        )
