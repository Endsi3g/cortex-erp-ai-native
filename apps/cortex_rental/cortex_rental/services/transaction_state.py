"""
Transaction lifecycle state machine.
Enforces preconditions for Quote -> Reservation -> Contract -> Checked Out -> Returned -> Closed.
"""

from typing import Any, Optional, Tuple

try:
    import frappe
except ImportError:
    frappe = None


class TransactionStateService:
    VALID_TRANSITIONS = {
        "Quote": ["Reservation", "Cancelled"],
        "Reservation": ["Contract", "Quote", "Cancelled"],
        "Contract": ["Checked Out", "Cancelled"],
        "Checked Out": ["Returned", "Disputed"],
        "Returned": ["Closed", "Quarantine"],
        "Closed": [],
        "Cancelled": [],
        "Disputed": ["Closed", "Cancelled"],
        "Quarantine": ["Returned", "Closed"],
    }

    @classmethod
    def can_transition(
        cls, current_state: str, target_state: str, transaction_doc: Any, is_agent: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if transaction can transition to target state based on business rules.
        """
        if target_state not in cls.VALID_TRANSITIONS.get(current_state, []):
            return False, f"Invalid state transition from [{current_state}] to [{target_state}]."

        # Agents cannot autonomously confirm reservations or contracts
        if is_agent and target_state in ["Reservation", "Contract", "Closed"]:
            return (
                False,
                f"Agents are not permitted to transition transaction to [{target_state}] autonomously. Approval required.",
            )

        # Precondition checks for Contract
        if target_state == "Contract":
            if hasattr(transaction_doc, "customer_account_ready") and not transaction_doc.customer_account_ready:
                return (
                    False,
                    "Customer account readiness (onboarding & credit check) must be verified before confirming a contract.",
                )
            if hasattr(transaction_doc, "insurance_ready") and not transaction_doc.insurance_ready:
                return False, "Valid certificate of insurance (COI) is required before confirming a contract."
            if hasattr(transaction_doc, "payment_ready") and not transaction_doc.payment_ready:
                return False, "Security deposit or validated payment terms are required before confirming a contract."

        return True, None
