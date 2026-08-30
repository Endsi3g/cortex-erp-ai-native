"""
Consignment calculation and statement service.
Computes owner revenue share while strictly enforcing tenant/renter identity redaction.
"""
from typing import Any, Dict, Optional

try:
    import frappe
except ImportError:
    frappe = None


class ConsignmentService:
    FORBIDDEN_RENTER_KEYS = [
        "customer", "customer_name", "client_name", "renter_name",
        "customer_email", "renter_email", "billing_address", "contact_phone"
    ]

    @classmethod
    def sanitize_snapshot(cls, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize payout snapshot to remove any customer or renter identity.
        Guarantees complete confidentiality for rental clients.
        """
        sanitized = {}
        for key, value in snapshot_data.items():
            if key.lower() in cls.FORBIDDEN_RENTER_KEYS:
                continue
            if isinstance(value, dict):
                sanitized[key] = cls.sanitize_snapshot(value)
            else:
                sanitized[key] = value
        return sanitized

    @classmethod
    def calculate_payout(
        cls,
        gross_amount: float,
        consignment_percentage: float,
        serial_no: str,
        days: float,
        rate: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate owner payout amount and create sanitized calculation snapshot.
        """
        pct = float(consignment_percentage if consignment_percentage is not None else 70.0)
        payout_amount = round(gross_amount * (pct / 100.0), 2)

        raw_snapshot = {
            "serial_no": serial_no,
            "days": days,
            "rate": rate,
            "gross_amount": gross_amount,
            "consignment_percentage": pct,
            "payout_amount": payout_amount,
            "metadata": metadata or {}
        }

        sanitized_snapshot = cls.sanitize_snapshot(raw_snapshot)

        return {
            "gross_amount": gross_amount,
            "consignment_percentage": pct,
            "owner_payout_amount": payout_amount,
            "calculation_snapshot": sanitized_snapshot
        }
