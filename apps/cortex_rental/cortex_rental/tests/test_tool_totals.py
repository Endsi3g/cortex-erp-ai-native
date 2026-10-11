"""Les listes de l'assistant disent combien il y en a VRAIMENT (sans banc Frappe pour le pur; banc pour le réel)."""

import unittest

from cortex_rental.services.ai import tools

try:
    import frappe
except ImportError:
    frappe = None


class TestPaged(unittest.TestCase):
    def test_paged_reports_shown_total_and_truncation(self):
        out = tools._paged([{"name": "a"}] * 10, 34, "rentals")
        self.assertEqual((out["shown"], out["total"], out["truncated"]), (10, 34, True))
        self.assertFalse(tools._paged([{"name": "a"}] * 3, 3, "x")["truncated"])
        self.assertFalse(tools._paged([], 0, "x")["truncated"])

    def test_unknown_total_never_claims_truncation(self):
        self.assertFalse(tools._paged([{"name": "a"}], -1, "x")["truncated"])  # -1 = total introuvable

    def test_system_prompt_tells_the_model_to_say_ten_of_thirty_four(self):
        from cortex_rental.services.ai.gateway import SYSTEM_PROMPT

        self.assertIn("truncated", SYSTEM_PROMPT)
        self.assertIn("10 sur 34", SYSTEM_PROMPT)


@unittest.skipUnless(frappe, "requires a live Frappe site (bench)")
class TestTotalsLive(unittest.TestCase):
    def test_list_rentals_total_matches_the_database_and_flags_truncation(self):
        from cortex_rental.tests.live_fixtures import ensure_company, human_operator

        frappe.set_user("Administrator")
        ensure_company("Cortex Test Co A", "CTA")
        user = human_operator("Cortex Test Co A")
        frappe.set_user(user)
        out = tools.list_rentals(limit=1)
        real = frappe.db.count("Cortex Rental Transaction", {"company": "Cortex Test Co A"})
        self.assertEqual(out["total"], real)
        self.assertEqual(out["shown"], len(out["rentals"]))
        self.assertEqual(out["truncated"], real > 1)
        frappe.set_user("Administrator")


if __name__ == "__main__":
    unittest.main()
