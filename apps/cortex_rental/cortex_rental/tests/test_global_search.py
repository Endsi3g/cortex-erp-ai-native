import unittest

from cortex_rental.tests.fake_frappe import fake_frappe, load


class TestGlobalSearch(unittest.TestCase):
    def _seed(self, frappe):
        frappe.tables["Cortex Rental Transaction"] = [
            {"name": "CR-TRX-1", "company": "A", "customer": "Dune", "rental_state": "Quote", "project_name": ""},
            {"name": "CR-TRX-2", "company": "B", "customer": "Other", "rental_state": "Quote", "project_name": ""},
        ]
        frappe.tables["Customer"] = [
            {"name": "Dune", "customer_name": "Dune Productions", "cortex_company": "A", "disabled": 0},
            {"name": "Other", "customer_name": "Other Co", "cortex_company": "B", "disabled": 0},
        ]
        frappe.tables["Cortex Rental Item Profile"] = [
            {"item_code": "ALEXA", "item_name": "Alexa 35", "category": "Camera Bodies", "company": "A"}
        ]
        frappe.tables["Serial No"] = [{"name": "SN-1", "item_code": "ALEXA", "company": "B", "cortex_status": "Active"}]

    def test_short_query_returns_nothing(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            self.assertEqual(load("cortex_rental.api.v1.search").search_handler("a", "A"), [])

    def test_results_never_cross_company(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            results = load("cortex_rental.api.v1.search").search_handler("du", "A")
            ids = {(r["type"], r["id"]) for r in results}
            self.assertIn(("rental", "CR-TRX-1"), ids)
            self.assertNotIn(("rental", "CR-TRX-2"), ids)
            self.assertNotIn(("customer", "Other"), ids)
            self.assertNotIn(("serial", "SN-1"), ids)


if __name__ == "__main__":
    unittest.main()
