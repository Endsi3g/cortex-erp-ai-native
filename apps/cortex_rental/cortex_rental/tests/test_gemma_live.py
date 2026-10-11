"""Cortex Gemma dans un VRAI bench : le patch de départ, l'offre du niveau et l'absence de clé."""

import unittest

try:
    import frappe
except ImportError:
    frappe = None


@unittest.skipUnless(frappe, "requires a live Frappe site (bench)")
class TestGemmaLive(unittest.TestCase):
    def test_patch_enables_the_tier_only_when_nothing_was_ever_saved(self):
        from cortex_rental.patches import set_gemma_tier_defaults

        frappe.set_user("Administrator")
        saved = {f: frappe.db.get_single_value("Cortex AI Settings", f) for f in set_gemma_tier_defaults.VALUES}
        try:
            frappe.db.sql("delete from `tabSingles` where doctype='Cortex AI Settings' and field like 'tier_gemma%'")
            set_gemma_tier_defaults.execute()
            self.assertEqual(int(frappe.db.get_single_value("Cortex AI Settings", "tier_gemma_enabled")), 1)
            # Une personne qui l'éteint ensuite : le patch ne le rallume jamais.
            frappe.db.set_single_value("Cortex AI Settings", "tier_gemma_enabled", 0)
            set_gemma_tier_defaults.execute()
            self.assertEqual(int(frappe.db.get_single_value("Cortex AI Settings", "tier_gemma_enabled")), 0)
        finally:
            for field, value in saved.items():
                frappe.db.set_single_value("Cortex AI Settings", field, value if value is not None else 0)

    def test_tier_is_offered_with_the_gemini_key_and_hidden_when_disabled(self):
        from cortex_rental.services.ai import settings as ai_settings

        values = ai_settings.load()
        values["api_key"] = "fake"
        values["tier_gemma_enabled"] = 1
        row = {t["key"]: t for t in ai_settings.tiers(values)}["gemma"]
        self.assertTrue(row["configured"])
        values["api_key"] = ""
        self.assertFalse({t["key"]: t for t in ai_settings.tiers(values)}["gemma"]["configured"])


if __name__ == "__main__":
    unittest.main()
