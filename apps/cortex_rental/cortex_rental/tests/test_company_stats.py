"""Statistiques de société : chaque bloc respecte les droits, `None` veut dire « hors de vos droits »."""

from datetime import datetime
from types import SimpleNamespace
import unittest

from cortex_rental.services import account_insights as ai
from cortex_rental.services import team_activity


def _fake(allowed_doctypes):
    counts = {"User": 3, "Cortex Rental Item Profile": 12, "Customer": 7, "Cortex Rental Transaction": 5}

    def sql(query, params=None, as_dict=False):
        if "Serial No" in query:
            return [SimpleNamespace(unit_state="Active", count=9), SimpleNamespace(unit_state="Quarantine", count=1)]
        return [SimpleNamespace(rental_state="Quote", count=2), SimpleNamespace(rental_state="Checked Out", count=3)]

    def get_all(doctype, filters=None, fields=None, **kw):
        return [SimpleNamespace(total=100.0, balance=40.0, count=2)]

    return SimpleNamespace(
        has_permission=lambda doctype, ptype="read": doctype in allowed_doctypes,
        db=SimpleNamespace(
            count=lambda doctype, filters=None: counts.get(doctype, 0),
            table_exists=lambda d: True,
            has_column=lambda d, c: True,
            sql=sql,
        ),
        get_all=get_all,
    )


class TestCompanyStats(unittest.TestCase):
    def setUp(self):
        self._saved = {k: getattr(ai, k, None) for k in ("frappe", "add_days", "now_datetime", "flt")}
        self._members = team_activity.company_members
        team_activity.company_members = lambda company: ["a@x.c", "b@x.c"]
        ai.add_days = lambda value, days: value
        ai.now_datetime = lambda: datetime(2026, 10, 7)
        ai.flt = lambda v: float(v or 0)

    def tearDown(self):
        for key, value in self._saved.items():
            setattr(ai, key, value)
        team_activity.company_members = self._members

    def test_full_rights_fill_every_block(self):
        ai.frappe = _fake(
            {
                "Cortex Rental Item Profile",
                "Customer",
                "Cortex Rental Transaction",
                "Cortex Rental Invoice",
                "Cortex Rental Payment",
            }
        )
        stats = ai.company_stats("Cortex Test", "a@x.c")
        self.assertEqual(stats["team"]["active"], 3)
        self.assertEqual(stats["equipment"], {"items": 12, "units": {"Active": 9, "Quarantine": 1}})
        self.assertEqual(stats["customers"], {"active": 7})
        self.assertEqual(stats["rentals"]["open"], 3)
        self.assertEqual(stats["rentals"]["quotes"], 2)
        self.assertEqual(stats["billing"]["outstanding"], 40.0)
        self.assertEqual(stats["billing"]["collected"], 100.0)

    def test_blocks_outside_the_persons_rights_are_none_not_zero(self):
        ai.frappe = _fake({"Cortex Rental Transaction"})
        stats = ai.company_stats("Cortex Test", "a@x.c")
        self.assertIsNone(stats["equipment"])
        self.assertIsNone(stats["customers"])
        self.assertIsNone(stats["billing"])
        self.assertIsNotNone(stats["rentals"])

    def test_payments_stay_hidden_without_the_payment_right(self):
        ai.frappe = _fake({"Cortex Rental Invoice"})
        stats = ai.company_stats("Cortex Test", "a@x.c")
        self.assertIsNotNone(stats["billing"])
        self.assertIsNone(stats["billing"]["collected"])
        self.assertIsNone(stats["rentals"])


if __name__ == "__main__":
    unittest.main()
