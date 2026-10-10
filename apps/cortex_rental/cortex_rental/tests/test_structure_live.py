"""Modification de structure dans un VRAI bench : catégorie et champ ajoutés, annulés sans perte de données."""

import unittest

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.tests.live_fixtures import ensure_company, ensure_profile, ensure_user, human_operator

COMPANY = "Cortex Test Co A"
PROFILE = "Cortex Rental Item Profile"


@unittest.skipUnless(frappe, "requires a live Frappe site (bench)")
class TestStructureLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cortex_rental.services import sector_templates, structure
        from cortex_rental.services.ai import actions, records

        cls.st, cls.sx, cls.actions, cls.records = sector_templates, structure, actions, records
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
        frappe.db.delete(
            "Custom Field", {"dt": ["in", list(cls.sx.STRUCTURE_TYPES)], "fieldname": ["like", "cx\\_test%"]}
        )
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.delete(
            "Cortex AI Action", {"requested_by": ("in", [self.owner, self.operator]), "status": "Proposed"}
        )
        self.st._set_categories(self.original)
        frappe.set_user(self.owner)
        self.tag = frappe.generate_hash(length=5)

    def tearDown(self):
        frappe.set_user("Administrator")

    def _go(self, action, args, user=None):
        user = user or self.owner
        block = self.actions.propose(action, args, COMPANY, user)
        return block, self.actions.decide(block["action_id"], True, COMPANY, user)

    def test_non_owner_is_refused_for_both_actions(self):
        frappe.set_user(self.operator)
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("add_category", {"category": "Drones"}, COMPANY, self.operator)
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose(
                "add_custom_field", {"doctype": PROFILE, "label": "Poids", "fieldtype": "Float"}, COMPANY, self.operator
            )

    def test_category_add_then_undo_and_refused_while_in_use(self):
        name = f"Drones {self.tag}"
        block = self.actions.propose("add_category", {"category": name}, COMPANY, self.owner)
        self.assertNotIn(name, self.st.categories())  # l'aperçu n'écrit rien
        out = self.actions.decide(block["action_id"], True, COMPANY, self.owner)
        self.assertTrue(out["ok"], out)
        self.assertIn(name, self.st.categories())
        self.assertIn(name, frappe.get_meta(PROFILE).get_field("category").options)
        with self.assertRaises(self.actions.ActionError):  # doublon (sans tenir compte de la casse)
            self.actions.propose("add_category", {"category": name.upper()}, COMPANY, self.owner)

        # Une fiche l'utilise : l'annulation refuse et ne retire rien.
        code = ensure_profile(COMPANY, f"itm-cat-{self.tag}", serialized=0, quantity=1, rate=10.0)
        frappe.db.set_value(PROFILE, {"item_code": code, "company": COMPANY}, "category", name)
        refused = self.actions.undo(block["action_id"], COMPANY, self.owner)
        self.assertFalse(refused["ok"])
        self.assertIn("utilisent", refused["message"])
        self.assertIn(name, self.st.categories())
        frappe.db.set_value(PROFILE, {"item_code": code, "company": COMPANY}, "category", "")
        done = self.actions.undo(block["action_id"], COMPANY, self.owner)
        self.assertTrue(done["ok"], done)
        self.assertNotIn(name, self.st.categories())

    def test_custom_field_lifecycle_empty_field_is_deleted_on_undo(self):
        label = f"Test plaque {self.tag}"
        block = self.actions.propose(
            "add_custom_field", {"doctype": PROFILE, "label": label, "fieldtype": "Texte court"}, COMPANY, self.owner
        )
        fieldname = self.sx.field_slug(label)
        self.assertFalse(frappe.get_meta(PROFILE).has_field(fieldname))  # aperçu : rien d'écrit
        out = self.actions.decide(block["action_id"], True, COMPANY, self.owner)
        self.assertTrue(out["ok"], out)
        frappe.clear_cache(doctype=PROFILE)
        self.assertTrue(frappe.get_meta(PROFILE).has_field(fieldname))
        with self.assertRaises(self.actions.ActionError):  # même libellé : refusé
            self.actions.propose(
                "add_custom_field", {"doctype": PROFILE, "label": label, "fieldtype": "Data"}, COMPANY, self.owner
            )
        done = self.actions.undo(block["action_id"], COMPANY, self.owner)
        self.assertTrue(done["ok"], done)
        self.assertIn("supprimé", done["message"])
        frappe.clear_cache(doctype=PROFILE)
        self.assertFalse(frappe.get_meta(PROFILE).has_field(fieldname))

    def test_custom_field_with_data_is_hidden_not_deleted_and_is_editable_by_the_assistant(self):
        label = f"Test poids {self.tag}"
        block, out = self._go("add_custom_field", {"doctype": PROFILE, "label": label, "fieldtype": "Float"})
        self.assertTrue(out["ok"], out)
        fieldname = self.sx.field_slug(label)
        code = ensure_profile(COMPANY, f"itm-cx-{self.tag}", serialized=0, quantity=1, rate=10.0)
        profile = frappe.db.get_value(PROFILE, {"item_code": code, "company": COMPANY}, "name")
        self.assertIn(fieldname, self.records.editable_map(PROFILE))

        edit = self.actions.propose(
            "update_field",
            {"doctype": PROFILE, "name": profile, "fieldname": fieldname, "value": "12,5"},
            COMPANY,
            self.owner,
        )
        self.assertTrue(self.actions.decide(edit["action_id"], True, COMPANY, self.owner)["ok"])
        self.assertEqual(float(frappe.db.get_value(PROFILE, profile, fieldname)), 12.5)
        detail = self.records.get(PROFILE, profile, COMPANY)
        self.assertIn(fieldname, detail["editable_fields"])
        self.assertEqual(float(detail["fields"][fieldname]), 12.5)

        done = self.actions.undo(block["action_id"], COMPANY, self.owner)
        self.assertTrue(done["ok"], done)
        self.assertIn("masqué", done["message"])
        self.assertEqual(float(frappe.db.get_value(PROFILE, profile, fieldname)), 12.5)  # données gardées
        self.assertNotIn(fieldname, self.records.editable_map(PROFILE))  # masqué : plus modifiable

    def test_custom_field_is_added_last_on_every_allowed_type(self):
        for doctype in self.sx.STRUCTURE_TYPES:
            label = f"Test fin {self.tag}"
            block, out = self._go("add_custom_field", {"doctype": doctype, "label": label, "fieldtype": "Date"})
            self.assertTrue(out["ok"], (doctype, out))
            frappe.clear_cache(doctype=doctype)
            names = [f.fieldname for f in frappe.get_meta(doctype).fields]
            self.assertEqual(names[-1], self.sx.field_slug(label), doctype)  # à la fin, jamais en tête
            self.assertTrue(self.actions.undo(block["action_id"], COMPANY, self.owner)["ok"])
            frappe.clear_cache(doctype=doctype)
            self.assertNotIn(self.sx.field_slug(label), [f.fieldname for f in frappe.get_meta(doctype).fields])

    def test_select_field_needs_choices_and_refused_inputs(self):
        for bad in (
            {"doctype": "User", "label": "Test x", "fieldtype": "Data"},
            {"doctype": PROFILE, "label": "Test lien", "fieldtype": "Link"},
            {"doctype": PROFILE, "label": "Test liste", "fieldtype": "Select", "options": "Un seul"},
            {"doctype": PROFILE, "label": "Item Name", "fieldtype": "Data"},  # libellé déjà existant
            {"doctype": PROFILE, "label": "", "fieldtype": "Data"},
        ):
            with self.assertRaises(self.actions.ActionError, msg=str(bad)):
                self.actions.propose("add_custom_field", bad, COMPANY, self.owner)
        label = f"Test carburant {self.tag}"
        block, out = self._go(
            "add_custom_field",
            {
                "doctype": PROFILE,
                "label": label,
                "fieldtype": "Liste de choix",
                "options": "Essence, Diesel, Électrique",
            },
        )
        self.assertTrue(out["ok"], out)
        fieldname = self.sx.field_slug(label)
        frappe.clear_cache(doctype=PROFILE)
        self.assertEqual(frappe.get_meta(PROFILE).get_field(fieldname).options, "Essence\nDiesel\nÉlectrique")
        self.assertTrue(self.actions.undo(block["action_id"], COMPANY, self.owner)["ok"])


if __name__ == "__main__":
    unittest.main()
