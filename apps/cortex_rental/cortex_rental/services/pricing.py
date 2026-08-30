"""
Pricing and duration computation service for Cortex Rental.
Enforces the canonical 7 calendar days = 3 billable days rule and tier discounts.
"""

from datetime import datetime
from typing import Optional, Tuple
import math

try:
    import frappe
except ImportError:
    frappe = None


class PricingService:
    @staticmethod
    def compute_billable_days(starts_at: str, ends_at: str, company: Optional[str] = None) -> Tuple[int, float]:
        """
        Calculate calendar days and billable days.
        Canonical rule: 7 calendar days = 3.0 billable days.
        """
        if isinstance(starts_at, str):
            dt_start = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
        else:
            dt_start = starts_at

        if isinstance(ends_at, str):
            dt_end = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
        else:
            dt_end = ends_at

        delta_seconds = (dt_end - dt_start).total_seconds()
        calendar_days = max(1, math.ceil(delta_seconds / 86400.0))

        billable_days = float(calendar_days)

        # Check for custom DB pricing rules if running in Frappe
        if frappe and company:
            try:
                rule = frappe.db.get_value(
                    "Rental Pricing Rule",
                    {"company": company, "is_active": 1, "calendar_days": calendar_days},
                    ["billable_days"],
                    as_dict=True,
                )
                if rule and rule.billable_days:
                    return calendar_days, float(rule.billable_days)
            except Exception:
                pass

        # Standard industry curve for audiovisual rental:
        if calendar_days == 1:
            billable_days = 1.0
        elif calendar_days == 2:
            billable_days = 1.5
        elif calendar_days == 3:
            billable_days = 2.0
        elif calendar_days == 4:
            billable_days = 2.5
        elif calendar_days in (5, 6, 7):
            billable_days = 3.0  # Weekly rate canonical 7d = 3d
        elif calendar_days <= 14:
            billable_days = 6.0
        elif calendar_days <= 30:
            billable_days = 10.0  # Monthly rate
        else:
            billable_days = float(calendar_days) * 0.4

        return calendar_days, round(billable_days, 2)

    @staticmethod
    def calculate_line_total(
        unit_rate: float, quantity: float, billable_days: float, discount_percentage: float = 0.0
    ) -> float:
        """Calculate line subtotal with billable days and discount."""
        gross = unit_rate * quantity * billable_days
        if discount_percentage > 0:
            gross = gross * (1.0 - (discount_percentage / 100.0))
        return round(gross, 2)
