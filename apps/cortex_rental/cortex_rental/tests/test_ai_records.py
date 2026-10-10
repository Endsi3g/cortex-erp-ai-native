"""Lecture et modification générique (liste blanche) : règles pures, sans banc Frappe."""

import json
import os
import unittest

from cortex_rental.services.ai import actions, records

DOCTYPE_DIR = os.path.join(os.path.dirname(__file__), "..", "cortex_rental", "doctype")


def fields_of(doctype: str):
    folder = doctype.lower().replace(" ", "_").replace("-", "_")
    path = os.path.join(DOCTYPE_DIR, folder, f"{folder}.json")
    if not os.path.exists(path):
        return None
    return {f["fieldname"]: f for f in json.load(open(path, encoding="utf-8"))["fields"]}


class TestCoerce(unittest.TestCase):
    def test_numbers_accept_french_notation_and_refuse_junk(self):
        self.assertEqual(records.coerce_value("Currency", "1 250,5", "Tarif"), 1250.5)
        self.assertEqual(records.coerce_value("Int", "3", "Quantité"), 3)
        for bad in ("abc", "", None, True, "-5", "nan", "inf"):
            with self.assertRaises(actions.ActionError, msg=repr(bad)):
                records.coerce_value("Currency", bad, "Tarif")
        with self.assertRaises(actions.ActionError):
            records.coerce_value("Int", "2.5", "Quantité")
        with self.assertRaises(actions.ActionError):
            records.coerce_value("Percent", "120", "Taux")

    def test_check_select_and_text(self):
        self.assertEqual(records.coerce_value("Check", "Oui", "Active"), 1)
        self.assertEqual(records.coerce_value("Check", "non", "Active"), 0)
        with self.assertRaises(actions.ActionError):
            records.coerce_value("Check", "peut-être", "Active")
        self.assertEqual(records.coerce_value("Select", "B", "Choix", "A\nB\nC"), "B")
        with self.assertRaises(actions.ActionError):
            records.coerce_value("Select", "Z", "Choix", "A\nB")
        self.assertEqual(records.coerce_value("Data", "  Caméra   A7  ", "Nom"), "Caméra A7")
        with self.assertRaises(actions.ActionError):
            records.coerce_value("Data", "x" * 200, "Nom")

    def test_unsupported_types_are_refused(self):
        for ft in ("Link", "Table", "Date", "Attach", "Password"):
            with self.assertRaises(actions.ActionError, msg=ft):
                records.coerce_value(ft, "x", "Champ")


class TestCompare(unittest.TestCase):
    def test_same_value(self):
        self.assertTrue(records.same_value("Currency", 150, "150.000000"))
        self.assertTrue(records.same_value("Data", None, ""))
        self.assertTrue(records.same_value("Check", 1, True))
        self.assertFalse(records.same_value("Currency", 150, 150.01))
        self.assertFalse(records.same_value("Data", "a", "b"))

    def test_display_and_storable(self):
        self.assertEqual(records.display_value("Check", 1), "Oui")
        self.assertEqual(records.display_value("Data", ""), "(vide)")
        self.assertIn("$", records.display_value("Currency", 150))
        self.assertEqual(records.storable("Currency", "12.5"), 12.5)
        self.assertEqual(records.storable("Data", None), "")
        json.dumps(records.storable("Currency", 3))  # sérialisable sans perte


class TestRegistry(unittest.TestCase):
    def test_editable_fields_exist_are_writable_and_supported(self):
        """Une faute de frappe dans la liste blanche ou un champ devenu en lecture seule doit casser ce test."""
        for doctype, allowed in records.EDITABLE.items():
            meta = fields_of(doctype)
            if meta is None:  # type d'ERPNext (Customer) : vérifié dans le banc
                continue
            for fieldname in allowed:
                self.assertIn(fieldname, meta, f"{doctype}.{fieldname}")
                self.assertFalse(meta[fieldname].get("read_only"), f"{doctype}.{fieldname} est en lecture seule")
                self.assertIn(meta[fieldname]["fieldtype"], records.SUPPORTED, f"{doctype}.{fieldname}")

    def test_nothing_sensitive_is_editable(self):
        banned = {
            "status",
            "rental_state",
            "docstatus",
            "company",
            "grand_total",
            "subtotal",
            "balance",
            "total",
            "amount",
        }
        for doctype, allowed in records.EDITABLE.items():
            self.assertFalse(banned & set(allowed), doctype)
            self.assertFalse([f for f in allowed if f.startswith("acct_")], doctype)

    def test_every_editable_type_is_also_readable(self):
        self.assertFalse(set(records.EDITABLE) - set(records.READABLE))

    def test_readable_list_fields_exist(self):
        for doctype, spec in records.READABLE.items():
            meta = fields_of(doctype)
            if meta is None:
                continue
            for f in spec.list_fields + spec.search_fields:
                self.assertTrue(f == "name" or f in meta, f"{doctype}.{f}")
            self.assertIn(spec.company_field, meta)

    def test_update_is_an_undoable_action_without_global_right(self):
        spec = actions.ACTIONS["update_field"]
        self.assertIsNotNone(spec.undo)
        self.assertTrue(spec.effects)
        self.assertEqual(spec.doctype, "")


if __name__ == "__main__":
    unittest.main()
