import json
from typing import Optional

try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    class Document:
        pass
    frappe = None

from cortex_rental.cortex_rental.doctype.audit_event.audit_event import log_audit_event

class ApprovalRequest(Document):
    """
    Supervision queue entity for sensitive AI agent actions.
    Enforces that agents can never approve their own or any approval requests.
    """
    def approve(self, reason: Optional[str] = None):
        if frappe:
            current_user = frappe.session.user
            user_roles = frappe.get_roles(current_user)

            # Strict Agent Gate: Agents can never approve
            if "Agent Service Account" in user_roles or getattr(frappe.flags, "in_agent_context", False):
                frappe.throw("Agents are strictly forbidden from approving requests.", frappe.PermissionError)

            if self.status != "Pending":
                frappe.throw(f"Cannot approve an approval request in status [{self.status}].", frappe.ValidationError)

            self.status = "Approved"
            self.decided_by = current_user
            self.decision_reason = reason
            self.decided_at = frappe.utils.now_datetime()
            self.save()

            # Execute the approved mutation now, as the authenticated human
            # approver — never deferred to a later, unaudited step.
            self._execute_approved_action()

            log_audit_event(
                company=self.company,
                actor_type="Human",
                actor_id=current_user,
                action="rental.approval.approved",
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                after_state={"status": "Approved", "decision_reason": reason}
            )
        else:
            self.status = "Approved"

    def _execute_approved_action(self):
        """
        Perform the actual business mutation this request was approved
        for. Re-derives the target state from the structured
        `proposed_payload` (preferred) or the `action` identifier, then
        calls `transition_to()` so the same state-machine preconditions
        (customer account, insurance, payment) and audit trail apply as
        any other transition — approval never bypasses them.
        """
        if not frappe:
            return

        if self.entity_type == "Cortex Rental Transaction":
            target_state = self._resolve_target_rental_state()
            if not target_state:
                return
            txn = frappe.get_doc("Cortex Rental Transaction", self.entity_id)
            txn.transition_to(target_state, reason=f"Approved via {self.name}")

        elif self.entity_type == "Sales Order" and self.action == "rental.quote.transition_to_reservation":
            so = frappe.get_doc("Sales Order", self.entity_id)
            so.custom_rental_state = "Reservation"
            so.save()

    def _resolve_target_rental_state(self) -> Optional[str]:
        proposed = self.proposed_payload
        if proposed:
            try:
                proposed = json.loads(proposed) if isinstance(proposed, str) else proposed
            except (ValueError, TypeError):
                proposed = None
            if isinstance(proposed, dict) and proposed.get("rental_state"):
                return proposed["rental_state"]

        if self.action and "transition_to_" in self.action:
            suffix = self.action.rsplit("transition_to_", 1)[-1]
            return suffix.replace("_", " ").title()

        return None

    def reject(self, reason: str):
        if not reason or not reason.strip():
            if frappe:
                frappe.throw("A rejection reason is strictly required.", frappe.ValidationError)
            else:
                raise ValueError("Rejection reason required.")

        if frappe:
            current_user = frappe.session.user
            self.status = "Rejected"
            self.decided_by = current_user
            self.decision_reason = reason
            self.decided_at = frappe.utils.now_datetime()
            self.save()

            log_audit_event(
                company=self.company,
                actor_type="Human",
                actor_id=current_user,
                action="rental.approval.rejected",
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                after_state={"status": "Rejected", "decision_reason": reason}
            )
        else:
            self.status = "Rejected"
