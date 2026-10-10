"""
Check-in / partial-return / quarantine end-to-end regression suite.
Requires a live Frappe site — skipped in this sandbox. See
test_multitenant_isolation.py for the same pattern.
"""

import unittest

from cortex_rental.tests.live_fixtures import ensure_company, ensure_customer, ensure_profile, human_operator

try:
    import frappe
except ImportError:
    frappe = None


@unittest.skipUnless(frappe, "requires a live Frappe site (bench) — not available in this sandbox")
class TestCheckinLive(unittest.TestCase):
    def tearDown(self):
        frappe.set_user("Administrator")

    def _make_checked_out_transaction(self, company, item_code, qty, serial_nos):
        ensure_company(company, "CTA")
        ensure_profile(company, item_code, serialized=1)
        for sn in serial_nos:
            if not frappe.db.exists("Serial No", sn):
                frappe.get_doc(
                    {
                        "doctype": "Serial No",
                        "serial_no": sn,
                        "item_code": item_code,
                        "company": company,
                        "cortex_status": "Active",
                    }
                ).insert(ignore_permissions=True)
            # Un essai précédent a pu laisser ce numéro de série dans un autre état (réparation, quarantaine…).
            frappe.db.set_value("Serial No", sn, "cortex_status", "Active")
        txn = frappe.get_doc(
            {
                "doctype": "Cortex Rental Transaction",
                "company": company,
                "customer": ensure_customer("Client essai retours", company),
                "rental_state": "Quote",
                "starts_at": "2026-09-01 09:00:00",
                "ends_at": "2026-09-08 09:00:00",
                "customer_account_ready": 1,
                "insurance_ready": 1,
                "payment_ready": 1,
                "items": [{"item_code": item_code, "qty": qty, "rate": 100, "serial_no": serial_nos[0]}],
            }
        )
        txn.insert(ignore_permissions=True)
        # Les transitions sont faites par une personne de l'équipe : « Administrator » reçoit le rôle d'agent et serait refusé.
        frappe.set_user(human_operator(company))
        for state in ("Reservation", "Contract", "Checked Out"):
            txn.transition_to(state)
        return txn

    def test_partial_return_keeps_transaction_checked_out(self):
        from cortex_rental.services.checkin import complete_checkin

        company = "Cortex Test Co A"
        item_code = f"itm-checkin-partial-{frappe.generate_hash(length=6)}"  # un article neuf : les devis d'un essai précédent retiennent encore le matériel
        serial_nos = [f"{item_code}-SN-{i}" for i in range(2)]
        txn = self._make_checked_out_transaction(company, item_code, 2, serial_nos)

        checkin = frappe.get_doc(
            {
                "doctype": "Cortex Check-In",
                "company": company,
                "transaction": txn.name,
                "checked_in_by": "ops@cortex.local",
                "items": [
                    {
                        "transaction_item": txn.items[0].name,
                        "item_code": item_code,
                        "serial_no": serial_nos[0],
                        "expected_qty": 2,
                        "returned_qty": 1,
                        "condition": "Good",
                        "disposition": "Return to Stock",
                    }
                ],
            }
        )
        checkin.insert(ignore_permissions=True)
        result = complete_checkin(checkin.name, actor_id="ops@cortex.local")

        self.assertFalse(result["transaction_fully_returned"])
        txn.reload()
        self.assertEqual(txn.rental_state, "Checked Out")

    def test_full_return_transitions_transaction_to_returned(self):
        from cortex_rental.services.checkin import complete_checkin

        company = "Cortex Test Co A"
        item_code = f"itm-checkin-full-{frappe.generate_hash(length=6)}"
        serial_no = f"{item_code}-SN-0"
        txn = self._make_checked_out_transaction(company, item_code, 1, [serial_no])

        checkin = frappe.get_doc(
            {
                "doctype": "Cortex Check-In",
                "company": company,
                "transaction": txn.name,
                "checked_in_by": "ops@cortex.local",
                "items": [
                    {
                        "transaction_item": txn.items[0].name,
                        "item_code": item_code,
                        "serial_no": serial_no,
                        "expected_qty": 1,
                        "returned_qty": 1,
                        "condition": "Damaged",
                        "disposition": "Repair",
                    }
                ],
            }
        )
        checkin.insert(ignore_permissions=True)
        result = complete_checkin(checkin.name, actor_id="ops@cortex.local")

        self.assertTrue(result["transaction_fully_returned"])
        txn.reload()
        self.assertEqual(txn.rental_state, "Returned")
        self.assertEqual(frappe.db.get_value("Serial No", serial_no, "cortex_status"), "Under Repair")


if __name__ == "__main__":
    unittest.main()
