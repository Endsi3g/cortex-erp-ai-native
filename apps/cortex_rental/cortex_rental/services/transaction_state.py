"""
Transaction lifecycle state machine and ERPNext synchronization service.
Enforces preconditions for Quote -> Reservation -> Contract -> Checked Out -> Returned -> Closed.
"""

from cortex_rental.labels import state_label
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
            return (
                False,
                f"Transition d'état invalide : de « {state_label(current_state)} » vers « {state_label(target_state)} ».",
            )

        # Agents cannot autonomously confirm reservations or contracts
        if is_agent and target_state in ["Reservation", "Contract", "Closed"]:
            return (
                False,
                f"Un agent ne peut pas faire passer une location à l'état « {state_label(target_state)} » seul : une approbation humaine est requise.",
            )

        # Precondition checks for Contract
        if target_state == "Contract":
            if hasattr(transaction_doc, "customer_account_ready") and not transaction_doc.customer_account_ready:
                return (
                    False,
                    "Le compte client (mise en route et vérification de crédit) doit être vérifié avant de confirmer un contrat.",
                )
            if hasattr(transaction_doc, "insurance_ready") and not transaction_doc.insurance_ready:
                return False, "Un certificat d'assurance valide est requis avant de confirmer un contrat."
            if hasattr(transaction_doc, "payment_ready") and not transaction_doc.payment_ready:
                return (
                    False,
                    "Un dépôt de garantie ou des conditions de paiement validées sont requis avant de confirmer un contrat.",
                )

        return True, None

    @classmethod
    def sync_with_erpnext(cls, transaction_doc: Any) -> Optional[str]:
        """
        Synchronize Cortex Rental Transaction state with standard ERPNext documents (Quotation / Sales Order / Sales Invoice).
        """
        if not frappe:
            return None

        # Implementation of ERPNext doc creation or update
        try:
            if transaction_doc.rental_state == "Quote" and not transaction_doc.erpnext_quotation:
                q = frappe.get_doc(
                    {
                        "doctype": "Quotation",
                        "quotation_to": "Customer",
                        "party_name": transaction_doc.customer,
                        "company": transaction_doc.company,
                        "transaction_date": frappe.utils.today(),
                        "items": [],
                    }
                )
                for item in transaction_doc.items:
                    q.append(
                        "items",
                        {"item_code": item.item_code, "qty": item.qty, "rate": item.rate, "amount": item.amount},
                    )
                q.insert(ignore_permissions=True)
                transaction_doc.erpnext_quotation = q.name
                return q.name

            elif (
                transaction_doc.rental_state in ["Reservation", "Contract"] and not transaction_doc.erpnext_sales_order
            ):
                so = frappe.get_doc(
                    {
                        "doctype": "Sales Order",
                        "customer": transaction_doc.customer,
                        "company": transaction_doc.company,
                        "delivery_date": frappe.utils.getdate(transaction_doc.starts_at),
                        "items": [],
                    }
                )
                for item in transaction_doc.items:
                    so.append(
                        "items",
                        {"item_code": item.item_code, "qty": item.qty, "rate": item.rate, "amount": item.amount},
                    )
                so.insert(ignore_permissions=True)
                transaction_doc.erpnext_sales_order = so.name
                return so.name
        except Exception:
            pass

        return None
