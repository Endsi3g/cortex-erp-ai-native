from typing import Optional

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
from cortex_rental.services.availability import AvailabilityService
from cortex_rental.services.locking import reservation_lock

# States that block inventory (PRD §4). Confirming into one of these
# must happen under the per-item reservation lock, with a fresh
# availability re-check — a positive read-only availability check made
# moments earlier (ADR-002) is not a guarantee.
BLOCKING_STATES = {"Reservation", "Contract"}


class CortexRentalTransaction(Document):
    """
    Primary Transaction Hub for Cortex Rental Operations.
    Manages rental lifecycle Quote -> Reservation -> Contract -> Checked Out -> Returned -> Closed.
    """

    def validate(self):
        # 0. Enforce the lifecycle state machine unconditionally, regardless
        #    of entry path (Desk UI save, generic REST write, whitelisted
        #    API, MCP). transition_to() alone is not sufficient: any write
        #    that reaches validate() must be checked, or a direct field
        #    update can silently skip agent gating, preconditions and audit.
        self._enforce_state_transition()

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
                item.amount = PricingService.calculate_line_total(unit_rate, qty, self.billable_days, discount)
                subtotal += item.amount

        self.subtotal = round(subtotal, 2)
        tax_rate = float(self.tax_rate or 0.0)
        self.tax_amount = round(self.subtotal * (tax_rate / 100.0), 2)
        self.grand_total = round(self.subtotal + self.tax_amount, 2)

    @staticmethod
    def _current_actor_is_agent() -> bool:
        if not frappe:
            return False
        roles = frappe.get_roles(frappe.session.user)
        return "Agent Service Account" in roles or getattr(frappe.flags, "in_agent_context", False)

    def _enforce_state_transition(self):
        """
        Guard every save against an out-of-band state change. Runs on
        every validate(), not only when called via transition_to() — a
        direct doc.save() (Desk UI, generic REST) must be caught too.
        """
        if not frappe:
            return

        if self.is_new():
            if self.rental_state and self.rental_state != "Quote":
                frappe.throw(
                    "New Cortex Rental Transaction records must be created in the "
                    "'Quote' state; use transition_to() to advance the lifecycle.",
                    frappe.PermissionError,
                )
            return

        previous_state = frappe.db.get_value(self.doctype, self.name, "rental_state")
        if previous_state is None or previous_state == self.rental_state:
            return

        allowed, error_msg = TransactionStateService.can_transition(
            current_state=previous_state,
            target_state=self.rental_state,
            transaction_doc=self,
            is_agent=self._current_actor_is_agent(),
        )
        if not allowed:
            frappe.throw(error_msg, frappe.PermissionError)

    def transition_to(self, new_state: str, reason: Optional[str] = None):
        """
        Transition transaction to a new state with strict policy checks and audit trail.
        """
        is_agent = self._current_actor_is_agent()

        allowed, error_msg = TransactionStateService.can_transition(
            current_state=self.rental_state, target_state=new_state, transaction_doc=self, is_agent=is_agent
        )

        if not allowed:
            if frappe:
                frappe.throw(error_msg, frappe.PermissionError)
            else:
                raise PermissionError(error_msg)

        before_state = {"rental_state": self.rental_state}

        if frappe and new_state in BLOCKING_STATES:
            self._commit_transition_under_lock(new_state)
        else:
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
            after_state={"rental_state": new_state, "reason": reason},
        )

    def _commit_transition_under_lock(self, new_state: str):
        """
        Serialize "re-check availability, then flip state" per item so
        two concurrent confirmations of the last unit can't both
        succeed (ADR-002). The read-only availability check an operator
        or agent saw moments earlier is not a guarantee by itself.
        """
        item_codes = sorted({item.item_code for item in (self.items or []) if item.item_code})

        from contextlib import ExitStack

        with ExitStack() as locks:
            for code in item_codes:
                locks.enter_context(reservation_lock(self.company, code))

            item_requests = [{"item_id": item.item_code, "quantity": item.qty} for item in (self.items or [])]
            checks = AvailabilityService().check(
                company=self.company,
                starts_at=str(self.starts_at),
                ends_at=str(self.ends_at),
                item_requests=item_requests,
                exclude_transaction=self.name if not self.is_new() else None,
            )
            unavailable = [c["item_id"] for c in checks if not c["is_available"]]
            if unavailable:
                frappe.throw(
                    f"Cannot confirm {new_state}: insufficient availability for {', '.join(unavailable)} "
                    "in the requested window (re-checked under lock).",
                    frappe.ValidationError,
                )

            self.rental_state = new_state
            self.save()
