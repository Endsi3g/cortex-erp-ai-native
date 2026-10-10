"""Modèles de secteur dans un VRAI bench : aperçu, application, annulation, droits, catégories vues par Frappe."""

import unittest

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.tests.live_fixtures import ensure_company, ensure_profile, ensure_user, human_operator

COMPANY = "Cortex Test Co A"


@unittest.skipUnless(frappe, "requires a live Frappe site (bench)")
class TestSectorTemplatesLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cortex_rental.services import sector_templates
        from cortex_rental.services.ai import actions

        cls.st, cls.actions = sector_templates, actions
        frappe.set_user("Administrator")
        ensure_company(COMPANY, "CTA")
        cls.owner = ensure_user("owner-tpl@cortex.test", ["Cortex System Manager", "Rental Manager"], COMPANY)
        cls.operator = human_operator(COMPANY)
        cls.original = sector_templates.categories()
        frappe.flags.in_test = True

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        cls.st._set_categories(cls.original)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.delete(
            "Cortex AI Action", {"requested_by": ("in", [self.owner, self.operator]), "status": "Proposed"}
        )
        # Un site de départ connu : sans « Audio » ni « Lighting », sans les règles du modèle, acompte différent.
        self.st._set_categories([c for c in self.original if c not in ("Audio", "Lighting")])
        frappe.db.delete("Rental Pricing Rule", {"company": COMPANY, "rule_name": ("like", "%jours pour%")})
        if not frappe.db.exists("Cortex Finance Settings", COMPANY):
            frappe.get_doc({"doctype": "Cortex Finance Settings", "company": COMPANY}).insert(ignore_permissions=True)
        frappe.db.set_value("Cortex Finance Settings", COMPANY, {"deposit_percent": 10, "quote_hold_hours": 24})
        frappe.set_user(self.owner)

    def tearDown(self):
        frappe.set_user("Administrator")

    def _settings(self):
        return frappe.db.get_value(
            "Cortex Finance Settings", COMPANY, ["deposit_percent", "quote_hold_hours"], as_dict=True
        )

    def test_a_non_owner_cannot_propose_or_apply(self):
        frappe.set_user(self.operator)
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("apply_sector_template", {"template": "cinema_video"}, COMPANY, self.operator)

    def test_unknown_template_is_refused(self):
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("apply_sector_template", {"template": "xx"}, COMPANY, self.owner)

    def test_preview_writes_nothing_then_apply_then_undo_restores_everything(self):
        block = self.actions.propose("apply_sector_template", {"template": "cinema_video"}, COMPANY, self.owner)
        labels = " | ".join(f"{r['label']} {r.get('detail', '')}" for r in block["rows"])
        self.assertIn("Audio", labels)
        self.assertIn("7 jours pour 3", labels)
        self.assertIn("Avant : 10", labels)
        self.assertEqual(block["undo_label"], "Annuler ce modèle")
        # Rien d'écrit à l'aperçu.
        self.assertNotIn("Audio", self.st.categories())
        self.assertFalse(frappe.db.exists("Rental Pricing Rule", {"company": COMPANY, "rule_name": "7 jours pour 3"}))
        self.assertEqual(float(self._settings().deposit_percent), 10)

        out = self.actions.decide(block["action_id"], True, COMPANY, self.owner)
        self.assertTrue(out["ok"], out)
        self.assertTrue(out["can_undo"])
        self.assertTrue({"Audio", "Lighting"} <= set(self.st.categories()))
        # Frappe lui-même accepte maintenant la catégorie (liste du site, pas seulement l'interface).
        self.assertIn("Audio", frappe.get_meta("Cortex Rental Item Profile").get_field("category").options)
        week = frappe.db.get_value(
            "Rental Pricing Rule",
            {"company": COMPANY, "rule_name": "7 jours pour 3"},
            ["calendar_days", "billable_days", "is_active"],
            as_dict=True,
        )
        self.assertEqual((week.calendar_days, float(week.billable_days), week.is_active), (7, 3.0, 1))
        weekend = frappe.db.get_value("Rental Pricing Rule", {"company": COMPANY, "calendar_days": 3}, "is_active")
        self.assertEqual(weekend, 0)  # suggestion créée inactive
        self.assertEqual(float(self._settings().deposit_percent), 30)
        self.assertEqual(self._settings().quote_hold_hours, 72)

        # Déjà appliqué : plus rien à faire.
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("apply_sector_template", {"template": "cinema_video"}, COMPANY, self.owner)

        undone = self.actions.undo(block["action_id"], COMPANY, self.owner)
        self.assertTrue(undone["ok"], undone)
        self.assertEqual(undone["status"], "Undone")
        self.assertNotIn("Audio", self.st.categories())
        self.assertFalse(frappe.db.exists("Rental Pricing Rule", {"company": COMPANY, "rule_name": "7 jours pour 3"}))
        self.assertEqual(float(self._settings().deposit_percent), 10)
        self.assertEqual(self._settings().quote_hold_hours, 24)

    def test_undo_keeps_a_used_category_and_a_setting_changed_since(self):
        block = self.actions.propose("apply_sector_template", {"template": "cinema_video"}, COMPANY, self.owner)
        self.assertTrue(self.actions.decide(block["action_id"], True, COMPANY, self.owner)["ok"])
        code = ensure_profile(COMPANY, f"itm-aud-{frappe.generate_hash(length=6)}", serialized=0, quantity=2, rate=40.0)
        frappe.db.set_value("Cortex Rental Item Profile", {"item_code": code, "company": COMPANY}, "category", "Audio")
        frappe.db.set_value("Cortex Finance Settings", COMPANY, "deposit_percent", 45)
        undone = self.actions.undo(block["action_id"], COMPANY, self.owner)
        self.assertTrue(undone["ok"], undone)
        self.assertIn("Audio", self.st.categories())  # utilisée : jamais retirée
        self.assertNotIn("Lighting", self.st.categories())
        self.assertIn("Audio", undone["message"])
        self.assertIn("Acompte", undone["message"])  # réglage modifié depuis : laissé en place et dit
        self.assertEqual(float(self._settings().deposit_percent), 45)
        self.assertEqual(self._settings().quote_hold_hours, 24)
        frappe.db.set_value("Cortex Rental Item Profile", {"item_code": code, "company": COMPANY}, "category", "")

    def test_only_the_requester_can_undo_a_template(self):
        block = self.actions.propose("apply_sector_template", {"template": "cinema_video"}, COMPANY, self.owner)
        self.actions.decide(block["action_id"], True, COMPANY, self.owner)
        with self.assertRaises(self.actions.ActionError):
            self.actions.undo(block["action_id"], COMPANY, self.operator)


if __name__ == "__main__":
    unittest.main()
