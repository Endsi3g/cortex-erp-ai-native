"""Visite guidée : l'état « déjà vue » est gardé côté serveur, par personne, dans un VRAI bench."""

import unittest

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.tests.live_fixtures import ensure_company, ensure_user

COMPANY = "Cortex Test Co A"


@unittest.skipUnless(frappe, "requires a live Frappe site (bench)")
class TestTourLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cortex_rental.api.v1 import tour

        cls.tour = tour
        frappe.set_user("Administrator")
        ensure_company(COMPANY, "CTA")
        cls.a = ensure_user("tour-a@cortex.test", ["Rental Manager"], COMPANY)
        cls.b = ensure_user("tour-b@cortex.test", ["Rental Manager"], COMPANY)

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.delete("Cortex User Preference", {"user": ("in", [self.a, self.b])})

    def test_unseen_until_marked_then_seen_for_that_person_only(self):
        self.assertFalse(self.tour.tour_seen(self.a))
        self.tour.mark_seen_for(self.a)
        self.assertTrue(self.tour.tour_seen(self.a))
        self.assertFalse(self.tour.tour_seen(self.b))  # une autre personne la verra encore

    def test_marking_twice_and_with_existing_preferences_row(self):
        frappe.get_doc({"doctype": "Cortex User Preference", "user": self.a}).insert(ignore_permissions=True)
        self.tour.mark_seen_for(self.a)
        self.tour.mark_seen_for(self.a)
        self.assertEqual(frappe.db.count("Cortex User Preference", {"user": self.a}), 1)
        self.assertTrue(self.tour.tour_seen(self.a))

    def test_guest_and_unknown_never_get_a_tour(self):
        self.assertTrue(self.tour.tour_seen("Guest"))
        self.assertTrue(self.tour.tour_seen(""))

    def test_marking_clears_the_cached_boot_of_that_person(self):
        frappe.cache.hset("bootinfo", self.a, {"cortex_tour": {"seen": False}})
        self.tour.mark_seen_for(self.a)
        self.assertFalse(frappe.cache.hget("bootinfo", self.a))

    def test_notification_preferences_do_not_expose_the_tour_field(self):
        from cortex_rental.services import account_insights

        self.assertNotIn("tour_seen_at", account_insights.PREFERENCE_FIELDS)


if __name__ == "__main__":
    unittest.main()
