"""Owner statements computed from real rentals, on the fake frappe."""

import types
import unittest

from cortex_rental.tests.fake_frappe import fake_frappe, load

RENTAL_ROW = {
    "rental": "CR-TRX-1",
    "starts_at": "2026-09-02 08:00:00",
    "ends_at": "2026-09-09 18:00:00",
    "final_invoice": "SINV-1",
    "item_code": "ALEXA",
    "item_name": "ARRI Alexa 35",
    "qty": 2,
    "rate": 1500.0,
    "billable_days": 3.0,
    "amount": 8100.0,  # 2 units x 1500 x 3 days, 10 % discount
    "assigned_serials": '["SN-OWNED", "SN-HOUSE"]',
    "serial_no": None,
    # renter data that must never reach the owner
    "customer": "Dune 3 Productions",
    "project_name": "Arrakis",
}


class TestOwnerStatement(unittest.TestCase):
    def _seed(self, frappe):
        frappe.tables["Serial No"] = [
            {"name": "SN-OWNED", "company": "A", "cortex_consignment_owner": "OWN-RD"},
            {"name": "SN-HOUSE", "company": "A", "cortex_consignment_owner": None},
        ]
        frappe.tables["Consignment Owner"] = [
            {"name": "OWN-RD", "owner_name": "Roger D.", "short_code": "RD", "company": "A", "default_percentage": 70}
        ]
        frappe.tables["Company"] = [{"name": "A", "default_currency": "CAD"}]
        frappe.tables["Consignment Payout"] = []
        frappe.db.sql = lambda *args, **kwargs: [types.SimpleNamespace(**RENTAL_ROW)]
        frappe.utils.get_system_timezone = lambda: "America/Montreal"
        frappe.utils.now_datetime = lambda: "2026-10-01 09:00:00"

    def test_only_owned_units_count_at_the_owner_share_of_net_revenue(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            statement = load("cortex_rental.services.consignment").owner_statement("A", "OWN-RD", "2026-09")
            self.assertEqual([line["serial_number"] for line in statement["lines"]], ["SN-OWNED"])
            line = statement["lines"][0]
            self.assertEqual(line["discount_amount"], 450.0)  # 4500 gross - 4050 net per unit
            self.assertEqual(line["owner_amount"], 2835.0)  # 70 % of 4050
            self.assertEqual(statement["totals"], {"eligible_net_revenue": 4050.0, "owner_amount_due": 2835.0})
            self.assertEqual(statement["currency"], "CAD")

    def test_statement_never_carries_renter_identity(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            statement = load("cortex_rental.services.consignment").owner_statement("A", "OWN-RD", "2026-09")
            text = str(statement)
            for forbidden in ("Dune 3", "Arrakis", "customer", "project"):
                self.assertNotIn(forbidden, text)
            self.assertEqual(
                sorted(statement["lines"][0]),
                sorted(
                    [
                        "serial_number",
                        "equipment_name",
                        "rental_start_date",
                        "rental_end_date",
                        "billable_days",
                        "rate",
                        "discount_amount",
                        "consignment_percentage",
                        "owner_amount",
                        "invoice_reference",
                    ]
                ),
            )

    def test_other_company_owner_is_refused(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            with self.assertRaises(frappe.PermissionError):
                load("cortex_rental.services.consignment").owner_statement("B", "OWN-RD", "2026-09")


if __name__ == "__main__":
    unittest.main()
