"""Modèles de secteur : données et règles pures (sans banc Frappe)."""

import json
import os
import unittest

from cortex_rental.services import sector_templates as st
from cortex_rental.services.ai import actions, records

PROFILE_JSON = os.path.join(
    os.path.dirname(__file__),
    "..",
    "cortex_rental",
    "doctype",
    "cortex_rental_item_profile",
    "cortex_rental_item_profile.json",
)
RULE_JSON = os.path.join(
    os.path.dirname(__file__), "..", "cortex_rental", "doctype", "rental_pricing_rule", "rental_pricing_rule.json"
)


class TestPure(unittest.TestCase):
    def test_parse_options_drops_blanks_and_duplicates_keeping_order(self):
        self.assertEqual(st.parse_options("A\n\n B \nA\nC\n"), ["A", "B", "C"])
        self.assertEqual(st.parse_options(None), [])

    def test_merge_adds_only_missing_in_template_order(self):
        self.assertEqual(st.merge_categories(["A", "C"], ["A", "B", "C", "D"]), ["B", "D"])
        self.assertEqual(st.merge_categories(["A"], ["A"]), [])

    def test_removal_never_drops_a_category_in_use(self):
        self.assertEqual(st.without_categories(["A", "B", "C"], ["B", "C"], used=["C"]), ["A", "C"])
        self.assertEqual(st.without_categories(["A", "B"], ["B"], used=[]), ["A"])

    def test_unknown_template_is_refused_in_french(self):
        with self.assertRaises(ValueError) as ctx:
            st.template("inconnu")
        self.assertIn("n'existe pas", str(ctx.exception))
        self.assertEqual(st.catalog()[0]["key"], "cinema_video")


class TestTemplateData(unittest.TestCase):
    def test_cinema_categories_are_exactly_the_existing_ones(self):
        """Aucune donnée existante ne doit changer de catégorie : le modèle reprend la liste actuelle de la fiche."""
        options = [
            f for f in json.load(open(PROFILE_JSON, encoding="utf-8"))["fields"] if f["fieldname"] == "category"
        ][0]
        self.assertEqual(st.TEMPLATES["cinema_video"]["categories"], st.parse_options(options["options"]))

    def test_settings_are_only_editable_non_legal_fields(self):
        allowed = set(records.EDITABLE["Cortex Finance Settings"])
        for key, spec in st.TEMPLATES.items():
            self.assertFalse(set(spec["settings"]) - allowed, key)
            for name, value in spec["settings"].items():
                limit = records.MAX_VALUE.get(name)
                self.assertTrue(limit is None or value <= limit, f"{key}.{name}")

    def test_pricing_rules_use_real_rule_fields(self):
        fields = {f["fieldname"] for f in json.load(open(RULE_JSON, encoding="utf-8"))["fields"]}
        for key, spec in st.TEMPLATES.items():
            names = [r["rule_name"] for r in spec["pricing_rules"]]
            self.assertEqual(len(names), len(set(names)), key)
            for rule in spec["pricing_rules"]:
                self.assertTrue(set(rule) <= fields, f"{key}: {set(rule) - fields}")
                self.assertGreater(rule["calendar_days"], 0)
                self.assertGreater(rule["billable_days"], 0)
                self.assertLessEqual(rule["billable_days"], rule["calendar_days"])

    def test_the_action_is_registered_undoable_and_owner_gated(self):
        spec = actions.ACTIONS["apply_sector_template"]
        self.assertIsNotNone(spec.undo)
        self.assertTrue(spec.effects)
        self.assertEqual(spec.undo_label, "Annuler ce modèle")


if __name__ == "__main__":
    unittest.main()
