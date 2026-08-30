"""
Availability correctness + mutation-time concurrency regression suite.
Like test_multitenant_isolation.py, these require a live Frappe site
and MariaDB (Serial No records, Cortex Rental Transaction rows) and are
skipped in this sandbox. Written so the first real `bench run-tests`
proves:
  - a Serial No in Quarantine/Under Repair/Missing/Decommissioned status
    is excluded from the available fleet count,
  - a `Serial No` count of zero is reported as zero, not silently
    replaced by a hardcoded fallback,
  - two concurrent transition_to("Reservation") calls for the last unit
    cannot both succeed.
"""

import unittest

try:
    import frappe
except ImportError:
    frappe = None


@unittest.skipUnless(frappe, "requires a live Frappe site (bench) — not available in this sandbox")
class TestAvailabilityAndConcurrency(unittest.TestCase):
    def test_zero_serials_reports_zero_not_a_fake_fallback(self):
        from cortex_rental.services.availability import AvailabilityService

        result = AvailabilityService().check(
            company="Cortex Test Co A",
            starts_at="2026-09-01T09:00:00Z",
            ends_at="2026-09-08T09:00:00Z",
            item_requests=[{"item_id": "itm-does-not-exist", "quantity": 1}],
        )
        self.assertEqual(result[0]["total_fleet_quantity"], 0.0)
        self.assertFalse(result[0]["is_available"])

    def test_quarantined_serial_excluded_from_available_count(self):
        from cortex_rental.services.availability import AvailabilityService

        company = "Cortex Test Co A"
        item_code = "itm-quarantine-test-cam"
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc(
                {"doctype": "Item", "item_code": item_code, "item_name": item_code, "is_stock_item": 1}
            ).insert(ignore_permissions=True)

        for i in range(2):
            serial = f"{item_code}-SN-{i}"
            if not frappe.db.exists("Serial No", serial):
                frappe.get_doc(
                    {
                        "doctype": "Serial No",
                        "serial_no": serial,
                        "item_code": item_code,
                        "company": company,
                        "cortex_status": "Quarantine" if i == 0 else "Active",
                    }
                ).insert(ignore_permissions=True)

        result = AvailabilityService().check(
            company=company,
            starts_at="2026-09-01T09:00:00Z",
            ends_at="2026-09-08T09:00:00Z",
            item_requests=[{"item_id": item_code, "quantity": 2}],
        )
        self.assertEqual(result[0]["total_fleet_quantity"], 2.0)
        self.assertEqual(result[0]["unavailable_status_quantity"], 1.0)
        self.assertEqual(result[0]["available_quantity"], 1.0)
        self.assertFalse(result[0]["is_available"])  # 2 requested, only 1 truly available

    def test_second_concurrent_reservation_of_last_unit_is_rejected(self):
        """
        Simulates the race ADR-002/PRD-INV-003 targets: two transactions
        for the same single-unit item both pass an earlier read-only
        availability check, then both call transition_to("Reservation").
        The second one to acquire the lock must be rejected by the
        re-check under lock rather than silently double-booking the unit.
        """
        from cortex_rental.services.locking import reservation_lock

        company = "Cortex Test Co A"
        item_code = "itm-single-unit-test-cam"
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc(
                {"doctype": "Item", "item_code": item_code, "item_name": item_code, "is_stock_item": 1}
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("Serial No", f"{item_code}-SN-0"):
            frappe.get_doc(
                {
                    "doctype": "Serial No",
                    "serial_no": f"{item_code}-SN-0",
                    "item_code": item_code,
                    "company": company,
                    "cortex_status": "Active",
                }
            ).insert(ignore_permissions=True)

        # Holding the lock ourselves simulates a concurrent confirmation
        # already in flight; the transition attempt below must fail fast
        # rather than block indefinitely or bypass the lock.
        from cortex_rental.services.locking import ReservationLockError

        with reservation_lock(company, item_code):
            txn = frappe.get_doc(
                {
                    "doctype": "Cortex Rental Transaction",
                    "company": company,
                    "customer": frappe.db.get_value("Customer", {}, "name") or "Guest",
                    "rental_state": "Quote",
                    "starts_at": "2026-09-01 09:00:00",
                    "ends_at": "2026-09-08 09:00:00",
                    "items": [{"item_code": item_code, "qty": 1, "rate": 100}],
                }
            )
            txn.insert(ignore_permissions=True)
            with self.assertRaises(ReservationLockError):
                txn.transition_to("Reservation")


if __name__ == "__main__":
    unittest.main()
