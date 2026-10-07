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


class TestColleagueProfile(unittest.TestCase):
    def setUp(self):
        self._saved = {
            k: getattr(ai, k, None) for k in ("frappe", "add_days", "add_to_date", "now_datetime", "get_datetime")
        }
        self._members = team_activity.company_members
        team_activity.company_members = lambda company: ["ami@x.c"]
        ai.add_days = lambda value, days: value
        ai.add_to_date = lambda value, minutes=0: datetime(2026, 10, 7, 11, 57)
        ai.now_datetime = lambda: datetime(2026, 10, 7, 12, 0)
        ai.get_datetime = lambda v: v
        self._role = ai.role_summary
        self._logins = ai.login_count
        self._counts = ai._audit_counts
        ai.role_summary = lambda user: {"label": "Comptoir", "help": ""}
        ai.login_count = lambda user, since: 4
        ai._audit_counts = lambda company, user, since: {"a": 3, "b": 2}

        def throw(message, exc=None):
            raise (exc or Exception)(message)

        user = SimpleNamespace(
            full_name="Ami Test",
            user_image="/files/a.png",
            mobile_no="514-555-0100",
            creation=datetime(2026, 1, 1),
            last_login=datetime(2026, 10, 7, 9, 0),
            last_active=datetime(2026, 10, 7, 11, 59),
            enabled=1,
        )
        ai.frappe = SimpleNamespace(
            throw=throw,
            PermissionError=PermissionError,
            db=SimpleNamespace(get_value=lambda *a, **k: user),
            get_all=lambda *a, **k: [
                SimpleNamespace(action="cortex.rental_transaction.draft_created", creation=datetime(2026, 10, 7, 8, 0))
            ],
        )

    def tearDown(self):
        for key, value in self._saved.items():
            setattr(ai, key, value)
        ai.role_summary, ai.login_count, ai._audit_counts = self._role, self._logins, self._counts
        team_activity.company_members = self._members

    def test_a_colleague_profile_shows_contact_presence_and_recent_activity(self):
        profile = ai.colleague_profile("Cortex Test", "moi@x.c", "AMI@x.c")
        self.assertEqual(profile["name"], "Ami Test")
        self.assertEqual(profile["phone"], "514-555-0100")
        self.assertTrue(profile["online"])
        self.assertEqual(profile["actions_30d"], 5)
        self.assertEqual(profile["recent"][0]["text"], "Devis créé")
        self.assertIsNone(profile["usage_time"])  # jamais estimé
        self.assertFalse(profile["you"])

    def test_a_person_outside_the_company_is_refused(self):
        with self.assertRaises(PermissionError):
            ai.colleague_profile("Cortex Test", "moi@x.c", "autre@ailleurs.c")

    def test_the_viewer_can_open_their_own_profile(self):
        profile = ai.colleague_profile("Cortex Test", "ami@x.c", "ami@x.c")
        self.assertTrue(profile["you"])
