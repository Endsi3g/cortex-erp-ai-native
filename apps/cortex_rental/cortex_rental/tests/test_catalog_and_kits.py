"""Kit discount policy and pricing curve on the fake frappe."""

import unittest

from cortex_rental.tests.fake_frappe import fake_frappe, load


class TestKitDiscount(unittest.TestCase):
    def _seed(self, frappe):
        frappe.tables["Cortex Rental Kit"] = [
            {"name": "KIT-1", "company": "A", "is_active": 1, "discount_percentage": 10}
        ]
        frappe.tables["Cortex Rental Kit Item"] = [{"parent": "KIT-1", "item_code": "ALEXA"}]

    def test_exact_kit_discount_is_policy(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            self.assertTrue(load("cortex_rental.api.v1.rentals")._is_kit_discount("A", "KIT-1", "ALEXA", 10))

    def test_other_discount_item_or_company_is_not(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            rentals = load("cortex_rental.api.v1.rentals")
            self.assertFalse(rentals._is_kit_discount("A", "KIT-1", "ALEXA", 25))
            self.assertFalse(rentals._is_kit_discount("A", "KIT-1", "OTHER", 10))
            self.assertFalse(rentals._is_kit_discount("B", "KIT-1", "ALEXA", 10))
            self.assertFalse(rentals._is_kit_discount("A", None, "ALEXA", 10))


class TestPricingCurve(unittest.TestCase):
    def test_curve_uses_the_billable_days_rule(self):
        with fake_frappe() as frappe:
            frappe.tables["Rental Pricing Rule"] = []
            curve = load("cortex_rental.api.v1.catalog").pricing_curve(100.0, "A")
            by_days = {row["calendar_days"]: row for row in curve}
            self.assertEqual(by_days[7]["billable_days"], 3.0)
            self.assertEqual(by_days[7]["price"], 300.0)
            self.assertEqual(by_days[1]["price"], 100.0)


if __name__ == "__main__":
    unittest.main()


class TestAggregation(unittest.TestCase):
    def test_lines_of_the_same_item_are_checked_together(self):
        import types

        from cortex_rental.cortex_rental.doctype.cortex_rental_transaction.cortex_rental_transaction import (
            aggregate_item_requests,
        )

        rows = [
            types.SimpleNamespace(item_code="ALEXA", qty=1),
            types.SimpleNamespace(item_code="ALEXA", qty=2),
            types.SimpleNamespace(item_code="COOKE", qty=1),
        ]
        self.assertEqual(
            aggregate_item_requests(rows),
            [{"item_id": "ALEXA", "quantity": 3.0}, {"item_id": "COOKE", "quantity": 1.0}],
        )

    def test_staff_check_sums_duplicate_items(self):
        from cortex_rental.api.v1 import availability

        results = availability.check_availability_handler(
            {
                "starts_at": "2026-10-01 08:00:00",
                "ends_at": "2026-10-03 18:00:00",
                "items": [{"item_code": "ALEXA", "quantity": 1}, {"item_code": "ALEXA", "quantity": 2}],
            },
            "A",
        )
        self.assertEqual([(r["item_id"], r["requested_quantity"]) for r in results], [("ALEXA", 3.0)])
