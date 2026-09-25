"""Operations overview and rental lifecycle helpers on the fake frappe."""

import datetime
import types
import unittest

from cortex_rental.tests.fake_frappe import fake_frappe, load


def _utils(now):
    return types.SimpleNamespace(
        now_datetime=lambda: now,
        add_to_date=lambda value, hours=0: value + datetime.timedelta(hours=hours),
        today=lambda: str(now.date()),
        getdate=lambda value=None: datetime.date.fromisoformat(str(value)[:10]) if value else now.date(),
    )


class TestOperationsOverview(unittest.TestCase):
    def test_counts_are_scoped_and_classified(self):
        now = datetime.datetime(2026, 9, 25, 10, 0, 0)
        with fake_frappe() as frappe:
            frappe.utils = _utils(now)
            rt = "Cortex Rental Transaction"
            frappe.tables[rt] = [
                {
                    "name": "OUT-LATE",
                    "company": "A",
                    "customer": "C1",
                    "rental_state": "Checked Out",
                    "starts_at": "2026-09-20 08:00:00",
                    "ends_at": datetime.datetime(2026, 9, 24, 18),
                },
                {
                    "name": "DEP-1",
                    "company": "A",
                    "customer": "C1",
                    "rental_state": "Contract",
                    "starts_at": datetime.datetime(2026, 9, 25, 14),
                    "ends_at": "2026-09-27 18:00:00",
                    "customer_account_ready": 1,
                    "insurance_ready": 1,
                    "payment_ready": 0,
                },
                {
                    "name": "OTHER-CO",
                    "company": "B",
                    "customer": "C9",
                    "rental_state": "Checked Out",
                    "starts_at": "2026-09-20 08:00:00",
                    "ends_at": datetime.datetime(2026, 9, 24, 18),
                },
            ]
            frappe.tables["Customer"] = [{"name": "C1", "customer_name": "Dune"}]
            frappe.tables["Serial No"] = [
                {"name": "SN-Q", "item_code": "ALEXA", "company": "A", "cortex_status": "Quarantine"}
            ]
            frappe.tables["Approval Request"] = [
                {"company": "A", "status": "Pending"},
                {"company": "B", "status": "Pending"},
            ]
            frappe.tables["Cortex Inbound Request"] = []

            # the fake compares datetimes, so feed comparable values for the between filter
            ops = load("cortex_rental.api.v1.operations")
            data = ops.overview_handler("A", "2026-09-25")
            self.assertEqual([r["name"] for r in data["overdue"]], ["OUT-LATE"])
            self.assertEqual(data["kpis"]["approvals_pending"], 1)
            self.assertEqual(data["kpis"]["exceptions"], 1)
            self.assertEqual([r["name"] for r in data["at_risk"]], ["DEP-1"])
            self.assertEqual(data["at_risk"][0]["missing_requirements"], ["payment_ready"])
            self.assertEqual(data["overdue"][0]["customer_name"], "Dune")


class TestAvailableActions(unittest.TestCase):
    def _doc(self, state, **extra):
        return types.SimpleNamespace(rental_state=state, final_invoice=extra.get("final_invoice"))

    def test_actions_follow_the_state_machine(self):
        with fake_frappe(roles=["Rental Operator"]):
            rentals = load("cortex_rental.api.v1.rentals")
            self.assertEqual(
                rentals.available_actions(self._doc("Quote")), ["edit_quote", "confirm_reservation", "cancel"]
            )
            self.assertIn("checkout", rentals.available_actions(self._doc("Contract")))
            self.assertEqual(rentals.available_actions(self._doc("Returned")), ["prepare_final_invoice", "close"])
            self.assertEqual(rentals.available_actions(self._doc("Returned", final_invoice="SINV-1")), ["close"])
            self.assertEqual(rentals.available_actions(self._doc("Closed")), [])

    def test_only_verifiers_get_the_readiness_action(self):
        with fake_frappe(roles=["Rental Operator"]):
            self.assertNotIn(
                "verify_readiness", load("cortex_rental.api.v1.rentals").available_actions(self._doc("Reservation"))
            )
        with fake_frappe(roles=["Rental Manager"]):
            self.assertIn(
                "verify_readiness", load("cortex_rental.api.v1.rentals").available_actions(self._doc("Reservation"))
            )


if __name__ == "__main__":
    unittest.main()
