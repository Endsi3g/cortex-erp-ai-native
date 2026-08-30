"""
Transaction lifecycle state machine and ERPNext synchronization service.
Enforces preconditions for Quote -> Reservation -> Contract -> Checked Out -> Returned -> Closed.
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.pricing import PricingService


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
        "Quarantine": ["Returned", "Closed"]
    }

    @classmethod
    def can_transition(
        cls,
        current_state: str,
        target_state: str,
        transaction_doc: Any,
        is_agent: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if transaction can transition to target state based on business rules.
        """
        if target_state not in cls.VALID_TRANSITIONS.get(current_state, []):
            return False, f"Invalid state transition from [{current_state}] to [{target_state}]."

        # Agents cannot autonomously confirm reservations or contracts
        if is_agent and target_state in ["Reservation", "Contract", "Closed"]:
            return False, f"Agents are not permitted to transition transaction to [{target_state}] autonomously. Approval required."

        # Precondition checks for Contract
        if target_state == "Contract":
            if hasattr(transaction_doc, "customer_account_ready") and not transaction_doc.customer_account_ready:
                return False, "Customer account readiness (onboarding & credit check) must be verified before confirming a contract."
            if hasattr(transaction_doc, "insurance_ready") and not transaction_doc.insurance_ready:
                return False, "Valid certificate of insurance (COI) is required before confirming a contract."
            if hasattr(transaction_doc, "payment_ready") and not transaction_doc.payment_ready:
                return False, "Security deposit or validated payment terms are required before confirming a contract."

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
                q = frappe.get_doc({
                    "doctype": "Quotation",
                    "quotation_to": "Customer",
                    "party_name": transaction_doc.customer,
                    "company": transaction_doc.company,
                    "transaction_date": frappe.utils.today(),
                    "items": []
                })
                for item in transaction_doc.items:
                    q.append("items", {
                        "item_code": item.item_code,
                        "qty": item.qty,
                        "rate": item.rate,
                        "amount": item.amount
                    })
                q.insert(ignore_permissions=True)
                transaction_doc.erpnext_quotation = q.name
                return q.name

            elif transaction_doc.rental_state in ["Reservation", "Contract"] and not transaction_doc.erpnext_sales_order:
                so = frappe.get_doc({
                    "doctype": "Sales Order",
                    "customer": transaction_doc.customer,
                    "company": transaction_doc.company,
                    "delivery_date": frappe.utils.getdate(transaction_doc.starts_at),
                    "items": []
                })
                for item in transaction_doc.items:
                    so.append("items", {
                        "item_code": item.item_code,
                        "qty": item.qty,
                        "rate": item.rate,
                        "amount": item.amount
                    })
                so.insert(ignore_permissions=True)
                transaction_doc.erpnext_sales_order = so.name
                return so.name
        except Exception:
            pass

        return None
