"""Retenue du matériel par un devis : le contrat de code (le comportement réel est vérifié sur le banc)."""

import json
import os
import unittest

BASE = os.path.dirname(os.path.dirname(__file__))


def read(*parts):
    with open(os.path.join(BASE, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestHoldContract(unittest.TestCase):
    def test_only_active_unexpired_quote_holds_count_in_availability(self):
        sql = read("services", "availability.py")
        self.assertIn("t.rental_state = 'Quote' AND t.hold_status = 'Active' AND t.hold_until > NOW()", sql)
        self.assertIn("held_quantity", sql)

    def test_a_quote_never_counts_against_itself(self):
        self.assertIn("exclude_transaction=tx.name", read("services", "holds.py"))

    def test_the_hold_is_taken_under_the_per_item_reservation_lock(self):
        body = read("services", "holds.py").split("def evaluate")[1].split("\ndef ")[0]
        self.assertIn("reservation_lock(", body)
        self.assertLess(body.index("reservation_lock("), body.index("AvailabilityService()"))

    def test_insufficient_stock_creates_the_quote_but_no_hold_and_says_why(self):
        body = read("services", "holds.py")
        self.assertIn('"Insufficient"', body)
        self.assertIn("aucune retenue", body)

    def test_holds_expire_by_themselves_no_cron_needed_for_correctness(self):
        self.assertIn("hold_until > NOW()", read("services", "availability.py"))

    def test_every_creation_path_gets_a_hold_through_the_controller(self):
        src = read("cortex_rental", "doctype", "cortex_rental_transaction", "cortex_rental_transaction.py")
        self.assertIn("def after_insert", src)
        self.assertIn("holds.evaluate(self)", src)
        self.assertIn(
            "never blocks", src.replace("ne bloque jamais", "never blocks")
        )  # panne de retenue : devis créé quand même

    def test_a_shared_quote_keeps_the_stock_until_the_link_expires(self):
        self.assertIn("holds.extend_to(tx, expires)", read("services", "quote_share.py"))

    def test_the_grid_shows_held_units_apart_from_booked_ones(self):
        vue = read("public", "js", "cortex_availability", "CortexAvailability.vue")
        self.assertIn("function holding", vue)
        self.assertIn("Retenu par un devis", vue)

    def test_settings_are_per_company_with_the_hold_on_by_default(self):
        spec = json.loads(read("cortex_rental", "doctype", "cortex_finance_settings", "cortex_finance_settings.json"))
        fields = {f["fieldname"]: f for f in spec["fields"]}
        self.assertEqual(fields["quote_hold_enabled"]["default"], "1")
        self.assertEqual(fields["quote_hold_hours"]["default"], "72")

    def test_reminders_are_read_only_notifications(self):
        src = read("services", "reminders.py")
        self.assertNotIn("transition_to", src)
        self.assertIn("Notification Log", src)
        self.assertIn('"hourly"', read("hooks.py"))


if __name__ == "__main__":
    unittest.main()
