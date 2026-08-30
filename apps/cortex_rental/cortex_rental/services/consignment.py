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
    # Single source of truth for renter/customer PII keys forbidden from
    # an owner-facing consignment payout snapshot or statement. Also
    # imported verbatim by ConsignmentPayout.validate() so the API-layer
    # sanitization and the DocType-level backstop can never drift apart
    # again (they previously used two different, non-overlapping lists).
    FORBIDDEN_RENTER_KEYS = [
        "customer",
        "customer_name",
        "customer_email",
        "customer_phone",
        "client_name",
        "client_email",
        "client_company",
        "renter_name",
        "renter_email",
        "renter_company",
        "billing_address",
        "contact_phone",
        "contact_name",
    ]

    # Only these top-level fields are ever written into a payout
    # snapshot — an allowlist, not just a denylist, so a future field
    # added to the raw calculation input isn't included by default.
    ALLOWED_SNAPSHOT_KEYS = frozenset(
        {"serial_no", "days", "rate", "gross_amount", "consignment_percentage", "payout_amount", "metadata"}
    )

    @classmethod
    def sanitize_snapshot(cls, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize payout snapshot: keep only allowlisted top-level keys,
        then recursively strip any forbidden renter/customer identity key
        at any nesting level (defense in depth for free-form fields like
        `metadata`, which callers may populate with arbitrary content).
        """
        sanitized = {}
        for key, value in snapshot_data.items():
            if key not in cls.ALLOWED_SNAPSHOT_KEYS:
                continue
            sanitized[key] = cls._strip_forbidden_keys(value)
        return sanitized

    @classmethod
    def _strip_forbidden_keys(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: cls._strip_forbidden_keys(v) for k, v in value.items() if k.lower() not in cls.FORBIDDEN_RENTER_KEYS
            }
        if isinstance(value, list):
            return [cls._strip_forbidden_keys(v) for v in value]
        return value

    @classmethod
    def calculate_payout(
        cls,
        gross_amount: float,
        consignment_percentage: float,
        serial_no: str,
        days: float,
        rate: float,
        metadata: Optional[Dict[str, Any]] = None,
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
            "metadata": metadata or {},
        }

        sanitized_snapshot = cls.sanitize_snapshot(raw_snapshot)

        return {
            "gross_amount": gross_amount,
            "consignment_percentage": pct,
            "owner_payout_amount": payout_amount,
            "calculation_snapshot": sanitized_snapshot,
        }
