"""Advance + balance billing rules (services/billing.py) on the fake frappe."""

import unittest

from cortex_rental.tests.fake_frappe import fake_frappe, load

BILLING = "cortex_rental.services.billing"


def _rental(frappe, **values):
    row = {
        "doctype": "Cortex Rental Transaction",
        "name": "CR-TRX-1",
        "company": "A",
        "customer": "Dune",
        "rental_state": "Reservation",
        "erpnext_sales_order": "SO-1",
        "advance_amount": 0,
        "payment_ready": 0,
        "items": [],
    }
    row.update(values)
    frappe.tables.setdefault("Cortex Rental Transaction", []).append(dict(row))
    return frappe.get_doc("Cortex Rental Transaction", "CR-TRX-1")


class TestAdvance(unittest.TestCase):
    def test_share_plus_guarantee(self):
        with fake_frappe():
            billing = load(BILLING)
            settings = {"advance_percentage": 30.0, "include_equipment_guarantee": True}
            self.assertEqual(
                billing.compute_advance(1000.0, 500.0, settings),
                {"percentage_amount": 300.0, "guarantee_amount": 500.0, "total": 800.0},
            )

    def test_guarantee_can_be_disabled(self):
        with fake_frappe():
            billing = load(BILLING)
            settings = {"advance_percentage": 50.0, "include_equipment_guarantee": False}
            self.assertEqual(billing.compute_advance(200.0, 900.0, settings)["total"], 100.0)

    def test_default_settings_without_record(self):
        with fake_frappe() as frappe:
            frappe.tables["Cortex Company Settings"] = []
            frappe.tables["Sales Taxes and Charges Template"] = [{"name": "QC - A", "company": "A", "is_default": 1}]
            settings = load(BILLING).get_settings("A")
            self.assertEqual(settings["advance_percentage"], 30.0)
            self.assertTrue(settings["include_equipment_guarantee"])
            self.assertEqual(settings["taxes_and_charges"], "QC - A")
            self.assertFalse(settings["configured"])


class TestPaymentReadiness(unittest.TestCase):
    def test_ready_only_when_erpnext_advance_covers_the_request(self):
        with fake_frappe() as frappe:
            billing = load(BILLING)
            frappe.tables["Sales Order"] = [{"name": "SO-1", "advance_paid": 700.0}]
            doc = _rental(frappe, advance_amount=800.0)
            billing._refresh_payment_readiness(doc)
            self.assertEqual(doc.payment_ready, 0)
            frappe.tables["Sales Order"][0]["advance_paid"] = 800.0
            billing._refresh_payment_readiness(doc)
            self.assertEqual(doc.payment_ready, 1)


class TestCheckinCharges(unittest.TestCase):
    def _seed(self, frappe, **item):
        frappe.tables["Cortex Check-In"] = [{"name": "CHK-1", "transaction": "CR-TRX-1", "status": "Completed"}]
        row = {
            "parent": "CHK-1",
            "item_code": "ALEXA",
            "serial_no": "SN-1",
            "condition": "Good",
            "disposition": "Return to Stock",
            "expected_qty": 1,
            "returned_qty": 1,
            "estimated_repair_cost": 0,
        }
        row.update(item)
        frappe.tables["Cortex Check-In Item"] = [row]
        frappe.tables["Cortex Rental Item Profile"] = [
            {"company": "A", "item_code": "ALEXA", "replacement_value": 85000}
        ]

    def test_damage_and_loss_lines(self):
        with fake_frappe() as frappe:
            billing = load(BILLING)
            self._seed(frappe, condition="Damaged", estimated_repair_cost=450, returned_qty=1)
            doc = _rental(frappe, rental_state="Returned")
            charges = billing._checkin_charges(doc, {"damage_item": "DMG", "loss_item": "LOSS"})
            self.assertEqual([(c["item_code"], c["rate"]) for c in charges], [("DMG", 450.0)])

            self._seed(frappe, condition="Missing", disposition="Missing", returned_qty=0)
            charges = billing._checkin_charges(doc, {"damage_item": "DMG", "loss_item": "LOSS"})
            self.assertEqual([(c["item_code"], c["qty"], c["rate"]) for c in charges], [("LOSS", 1.0, 85000.0)])

    def test_unconfigured_item_refuses_instead_of_dropping_the_charge(self):
        with fake_frappe() as frappe:
            billing = load(BILLING)
            self._seed(frappe, condition="Damaged", estimated_repair_cost=450)
            doc = _rental(frappe, rental_state="Returned")
            with self.assertRaises(frappe.ValidationError):
                billing._checkin_charges(doc, {"damage_item": None, "loss_item": None})


if __name__ == "__main__":
    unittest.main()
