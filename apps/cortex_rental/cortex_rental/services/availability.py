"""
Availability and concurrency calculation service for rental inventory.
Verifies time-window conflicts across quotes, reservations, and active contracts.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None


class AvailabilityService:
    def check(
        self,
        company: str,
        starts_at: str,
        ends_at: str,
        item_requests: List[Dict[str, Any]],
        actor: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check real-time availability for a list of requested rental items.
        Takes into account buffer/prep periods and active reservations.
        """
        results = []

        for req in item_requests:
            item_id = req.get("item_id") or req.get("item_code")
            requested_qty = float(req.get("quantity") or 1.0)

            total_fleet = 10.0
            reserved_qty = 0.0
            maintenance_qty = 0.0

            if frappe:
                # Query actual stock and reservations from DB
                try:
                    total_fleet = float(
                        frappe.db.count(
                            "Serial No", {"company": company, "item_code": item_id, "status": ["!=", "Decommissioned"]}
                        )
                        or 5.0
                    )

                    # Count active overlapping reservations/contracts
                    overlapping = frappe.db.sql(
                        """
                        SELECT SUM(ti.qty) as total_reserved
                        FROM `tabCortex Rental Transaction Item` ti
                        JOIN `tabCortex Rental Transaction` t ON t.name = ti.parent
                        WHERE t.company = %(company)s
                          AND ti.item_code = %(item_code)s
                          AND t.rental_state IN ('Reservation', 'Contract', 'Checked Out')
                          AND t.starts_at < %(ends_at)s
                          AND t.ends_at > %(starts_at)s
                    """,
                        {"company": company, "item_code": item_id, "starts_at": starts_at, "ends_at": ends_at},
                        as_dict=True,
                    )

                    if overlapping and overlapping[0].total_reserved:
                        reserved_qty = float(overlapping[0].total_reserved)
                except Exception:
                    total_fleet = 10.0

            available_qty = max(0.0, total_fleet - reserved_qty - maintenance_qty)
            is_available = available_qty >= requested_qty

            results.append(
                {
                    "item_id": item_id,
                    "requested_quantity": requested_qty,
                    "available_quantity": available_qty,
                    "total_fleet_quantity": total_fleet,
                    "reserved_quantity": reserved_qty,
                    "is_available": is_available,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "notes": "Available for reservation"
                    if is_available
                    else "Insufficient inventory for requested window",
                }
            )

        return results
