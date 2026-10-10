"""Modification de structure : règles pures (sans banc Frappe)."""

import unittest

from cortex_rental.services import structure as sx
from cortex_rental.services.ai import actions, records


class TestPure(unittest.TestCase):
    def test_category_is_cleaned_and_bounded(self):
        self.assertEqual(sx.clean_category("  Véhicules   utilitaires "), "Véhicules utilitaires")
        for bad in ("", "a", None, "x" * 41):
            with self.assertRaises(actions.ActionError, msg=repr(bad)):
                sx.clean_category(bad)

    def test_field_slug_is_ascii_prefixed_and_short(self):
        self.assertEqual(sx.field_slug("Numéro de plaque"), "cx_numero_de_plaque")
        self.assertTrue(sx.field_slug("A" * 80).startswith("cx_"))
        self.assertLessEqual(len(sx.field_slug("A" * 80)), 27)
        self.assertEqual(sx.field_slug("Poids (kg)"), "cx_poids_kg")
        with self.assertRaises(actions.ActionError):
            sx.field_slug("!!!")

    def test_slug_never_collides_with_the_editable_whitelist_prefix_rule(self):
        self.assertTrue(sx.field_slug("Notes").startswith(records.CUSTOM_PREFIX))

    def test_type_accepts_code_or_french_name_and_refuses_the_rest(self):
        self.assertEqual(sx.normalize_type("currency"), "Currency")
        self.assertEqual(sx.normalize_type("Montant"), "Currency")
        self.assertEqual(sx.normalize_type("liste de choix"), "Select")
        for bad in ("Link", "Table", "Attach", "Code", "", None):
            with self.assertRaises(actions.ActionError, msg=repr(bad)):
                sx.normalize_type(bad)

    def test_choices(self):
        self.assertEqual(sx.clean_choices("Essence, Diesel;Électrique\nDiesel"), ["Essence", "Diesel", "Électrique"])
        for bad in ("", "Seul", ",".join(f"c{i}" for i in range(25)), "a," + "x" * 41):
            with self.assertRaises(actions.ActionError, msg=bad[:20]):
                sx.clean_choices(bad)

    def test_every_supported_field_type_is_supported_by_update_field(self):
        for code in sx.FIELD_TYPES:
            self.assertIn(code, records.SUPPORTED, code)

    def test_actions_are_registered_undoable_with_labels(self):
        for name in ("add_category", "add_custom_field"):
            spec = actions.ACTIONS[name]
            self.assertIsNotNone(spec.undo, name)
            self.assertTrue(spec.effects, name)
            self.assertEqual(spec.doctype, "")

    def test_date_values_are_validated(self):
        self.assertEqual(records.coerce_value("Date", "2026-11-03", "Échéance"), "2026-11-03")
        for bad in ("3 novembre", "2026-13-40", "", None):
            with self.assertRaises(actions.ActionError, msg=repr(bad)):
                records.coerce_value("Date", bad, "Échéance")


if __name__ == "__main__":
    unittest.main()
