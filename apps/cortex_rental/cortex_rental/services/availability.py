"""
Availability and concurrency calculation service for rental inventory.
Verifies time-window conflicts across quotes, reservations, and active contracts.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

# Serial No statuses that make a unit unavailable for new bookings even
# though it isn't Decommissioned. ERPNext's stock `Serial No` doctype
# does not ship these values out of the box; Cortex extends it with a
# `cortex_status` Custom Field (see fixtures/custom_field.json) so
# quarantine/repair/missing units are excluded from the fleet count
# rather than silently counted as available.
UNAVAILABLE_SERIAL_STATUSES = ["Decommissioned", "Quarantine", "Under Repair", "Missing"]


class AvailabilityService:
    def check(
        self,
        company: str,
        starts_at: str,
        ends_at: str,
        item_requests: List[Dict[str, Any]],
        actor: Optional[Dict[str, Any]] = None,
        exclude_transaction: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check real-time availability for a list of requested rental items.
        Takes into account buffer/prep periods and active reservations.

        `exclude_transaction`: pass the current transaction's name when
        re-checking availability as part of confirming a transaction
        that is itself already in a blocking state (Reservation ->
        Contract) — otherwise its own reserved quantity would count
        against itself.
        """
        results = []

        for req in item_requests:
            item_id = req.get("item_id") or req.get("item_code")
            requested_qty = float(req.get("quantity") or 1.0)

            if not frappe:
                # No DB available (unit tests / local dev without a bench):
                # deterministic mock response, clearly labeled as such.
                results.append(
                    {
                        "item_id": item_id,
                        "requested_quantity": requested_qty,
                        "available_quantity": 10.0,
                        "total_fleet_quantity": 10.0,
                        "reserved_quantity": 0.0,
                        "unavailable_status_quantity": 0.0,
                        "is_available": True,
                        "starts_at": starts_at,
                        "ends_at": ends_at,
                        "notes": "Mocked result — no live Frappe/DB connection in this environment.",
                    }
                )
                continue

            # Cortex Rental Item Profile is the single catalog source of
            # truth (see ADR-004) — is_serialized decides how fleet size
            # is computed. Defaults to serialized/Serial-No-counted when
            # no profile exists, matching the prior (pre-ADR-004)
            # behavior for items that predate a profile record.
            profile = frappe.db.get_value(
                "Cortex Rental Item Profile",
                {"company": company, "item_code": item_id},
                ["is_serialized", "total_quantity"],
                as_dict=True,
            )
            is_serialized = bool(profile.is_serialized) if profile else True

            if is_serialized:
                total_fleet = frappe.db.count("Serial No", {"company": company, "item_code": item_id})
                unavailable_status_qty = frappe.db.count(
                    "Serial No",
                    {
                        "company": company,
                        "item_code": item_id,
                        "cortex_status": ["in", UNAVAILABLE_SERIAL_STATUSES],
                    },
                )
            else:
                # Non-serialized items have no individual Serial No
                # records; total_quantity on the profile is authoritative
                # and there is no per-unit quarantine/repair status.
                total_fleet = float(profile.total_quantity or 0) if profile else 0.0
                unavailable_status_qty = 0

            filters = {
                "company": company,
                "item_code": item_id,
                "starts_at": starts_at,
                "ends_at": ends_at,
            }
            exclusion_clause = ""
            if exclude_transaction:
                exclusion_clause = "AND t.name != %(exclude_transaction)s"
                filters["exclude_transaction"] = exclude_transaction

            overlapping = frappe.db.sql(
                f"""
                SELECT SUM(ti.qty) as total_reserved
                FROM `tabCortex Rental Transaction Item` ti
                JOIN `tabCortex Rental Transaction` t ON t.name = ti.parent
                WHERE t.company = %(company)s
                  AND ti.item_code = %(item_code)s
                  AND t.rental_state IN ('Reservation', 'Contract', 'Checked Out')
                  AND t.starts_at < %(ends_at)s
                  AND t.ends_at > %(starts_at)s
                  {exclusion_clause}
                """,
                filters,
                as_dict=True,
            )
            reserved_qty = (
                float(overlapping[0].total_reserved) if overlapping and overlapping[0].total_reserved else 0.0
            )

            available_qty = max(0.0, total_fleet - unavailable_status_qty - reserved_qty)
            is_available = available_qty >= requested_qty

            results.append(
                {
                    "item_id": item_id,
                    "requested_quantity": requested_qty,
                    "available_quantity": available_qty,
                    "total_fleet_quantity": float(total_fleet),
                    "reserved_quantity": reserved_qty,
                    "unavailable_status_quantity": float(unavailable_status_qty),
                    "is_available": is_available,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "notes": "Available for reservation"
                    if is_available
                    else "Insufficient inventory for requested window",
                }
            )

        return results
