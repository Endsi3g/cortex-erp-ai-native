"""Lecture générique et modification d'un champ (avant/après, annulation) dans un VRAI bench Frappe.

Preuves : liste blanche respectée, société étanche, droits de Frappe, valeur périmée refusée, annulation seulement si
rien n'a changé depuis, journal d'audit."""

import unittest

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.tests.live_fixtures import (
    ensure_company,
    ensure_customer,
    ensure_profile,
    ensure_user,
    human_operator,
)

COMPANY, OTHER = "Cortex Test Co A", "Cortex Test Co B"


@unittest.skipUnless(frappe, "requires a live Frappe site (bench)")
class TestAIRecordsLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cortex_rental.services.ai import actions, records

        cls.actions, cls.records = actions, records
        frappe.set_user("Administrator")
        ensure_company(COMPANY, "CTA")
        ensure_company(OTHER, "CTB")
        cls.operator = human_operator(COMPANY)
        cls.reader = ensure_user("reader-only@cortex.test", ["Cortex Read Only"], COMPANY)
        cls.suffix = frappe.generate_hash(length=6)
        frappe.flags.in_test = True

    def setUp(self):
        # Les propositions laissées ouvertes par les essais précédents plafonnent à 20 par personne : on repart à zéro.
        frappe.db.delete(
            "Cortex AI Action", {"requested_by": ("in", [self.operator, self.reader]), "status": "Proposed"}
        )
        frappe.set_user(self.operator)
        self.code = f"itm-rec-{frappe.generate_hash(length=6)}"
        ensure_profile(COMPANY, self.code, serialized=0, quantity=5, rate=120.0)
        self.profile = frappe.db.get_value(
            "Cortex Rental Item Profile", {"item_code": self.code, "company": COMPANY}, "name"
        )

    def tearDown(self):
        frappe.set_user("Administrator")

    def _update(self, **over):
        args = {
            "doctype": "Cortex Rental Item Profile",
            "name": self.profile,
            "fieldname": "daily_rate",
            "value": "150,5",
            **over,
        }
        return self.actions.propose("update_field", args, COMPANY, self.operator, reason="Demandé.")

    def _rate(self):
        return frappe.db.get_value("Cortex Rental Item Profile", self.profile, "daily_rate")

    # --- lecture -----------------------------------------------------------------------------------------------------

    def test_find_is_scoped_to_the_company_and_gives_real_links(self):
        out = self.records.find("Cortex Rental Item Profile", self.code, COMPANY)
        self.assertEqual([r["name"] for r in out["records"]], [self.profile])
        self.assertTrue(out["records"][0]["href"].startswith("/app/cortex-rental-item-profile/"))
        self.assertEqual(self.records.find("Cortex Rental Item Profile", self.code, OTHER)["records"], [])

    def test_get_returns_simple_fields_and_refuses_other_company_or_unlisted_types(self):
        out = self.records.get("Cortex Rental Item Profile", self.profile, COMPANY)
        self.assertEqual(out["fields"]["daily_rate"], 120.0)
        self.assertIn("daily_rate", out["labels"])
        self.assertIn("daily_rate", out["editable_fields"])
        self.assertNotIn("image", out["fields"])
        with self.assertRaises(self.actions.ActionError):
            self.records.get("Cortex Rental Item Profile", self.profile, OTHER)
        with self.assertRaises(self.actions.ActionError):
            self.records.get("Cortex AI Settings", "Cortex AI Settings", COMPANY)
        with self.assertRaises(self.actions.ActionError):
            self.records.find("User", "admin", COMPANY)

    def test_the_reader_role_cannot_read_what_frappe_forbids(self):
        frappe.set_user(self.reader)
        if frappe.has_permission("Cortex Rental Invoice", "read"):
            self.skipTest("le rôle lecture seule peut lire les factures sur ce site")
        with self.assertRaises(self.actions.ActionError):
            self.records.find("Cortex Rental Invoice", "", COMPANY)

    def test_every_editable_field_exists_and_is_writable_on_the_real_meta(self):
        """Contrôle sur les vraies fiches (y compris Customer, d'ERPNext) : aucune faute de frappe dans la liste blanche."""
        for doctype, allowed in self.records.EDITABLE.items():
            meta = frappe.get_meta(doctype)
            for fieldname in allowed:
                df = meta.get_field(fieldname)
                self.assertIsNotNone(df, f"{doctype}.{fieldname}")
                self.assertFalse(df.read_only, f"{doctype}.{fieldname} est en lecture seule")
                self.assertIn(df.fieldtype, self.records.SUPPORTED, f"{doctype}.{fieldname}")
        for doctype, spec in self.records.READABLE.items():
            meta = frappe.get_meta(doctype)
            for f in spec.list_fields + spec.search_fields:
                self.assertTrue(f == "name" or meta.has_field(f), f"{doctype}.{f}")

    def test_finance_settings_are_editable_within_bounds_and_taxes_are_not(self):
        if not frappe.db.exists("Cortex Finance Settings", COMPANY):
            frappe.get_doc({"doctype": "Cortex Finance Settings", "company": COMPANY}).insert(ignore_permissions=True)
        base = {"doctype": "Cortex Finance Settings", "name": COMPANY}
        for bad in ({"fieldname": "tps_rate", "value": "0"}, {"fieldname": "deposit_percent", "value": "500"}):
            with self.assertRaises(self.actions.ActionError, msg=str(bad)):
                self.actions.propose("update_field", {**base, **bad}, COMPANY, self.operator)
        before = frappe.db.get_value("Cortex Finance Settings", COMPANY, "deposit_percent")
        value = 25 if float(before) != 25 else 35
        block = self.actions.propose(
            "update_field", {**base, "fieldname": "deposit_percent", "value": str(value)}, COMPANY, self.operator
        )
        self.assertTrue(self.actions.decide(block["action_id"], True, COMPANY, self.operator)["ok"])
        self.assertEqual(float(frappe.db.get_value("Cortex Finance Settings", COMPANY, "deposit_percent")), value)
        self.assertTrue(self.actions.undo(block["action_id"], COMPANY, self.operator)["ok"])
        self.assertEqual(
            float(frappe.db.get_value("Cortex Finance Settings", COMPANY, "deposit_percent")), float(before)
        )

    def test_serialized_fleet_quantity_and_consignment_owner(self):
        serial = ensure_profile(
            COMPANY, f"itm-ser-{frappe.generate_hash(length=6)}", serialized=1, quantity=0, rate=90.0
        )
        name = frappe.db.get_value("Cortex Rental Item Profile", {"item_code": serial, "company": COMPANY}, "name")
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose(
                "update_field",
                {"doctype": "Cortex Rental Item Profile", "name": name, "fieldname": "total_quantity", "value": "4"},
                COMPANY,
                self.operator,
            )
        block = self.actions.propose(
            "update_field",
            {
                "doctype": "Cortex Rental Item Profile",
                "name": self.profile,
                "fieldname": "total_quantity",
                "value": "8",
            },
            COMPANY,
            self.operator,
        )
        self.assertTrue(self.actions.decide(block["action_id"], True, COMPANY, self.operator)["ok"])
        self.assertEqual(frappe.db.get_value("Cortex Rental Item Profile", self.profile, "total_quantity"), 8)

        code = frappe.generate_hash(length=5).upper()
        owner = frappe.get_doc(
            {"doctype": "Consignment Owner", "company": COMPANY, "owner_name": f"Prêteur {code}", "short_code": code}
        ).insert(ignore_permissions=True)
        frappe.db.commit()
        found = self.records.find("Consignment Owner", code, COMPANY)
        self.assertEqual([r["name"] for r in found["records"]], [owner.name])
        phone = self.actions.propose(
            "update_field",
            {"doctype": "Consignment Owner", "name": owner.name, "fieldname": "phone", "value": "514 555-0100"},
            COMPANY,
            self.operator,
        )
        self.assertTrue(self.actions.decide(phone["action_id"], True, COMPANY, self.operator)["ok"])
        self.assertEqual(frappe.db.get_value("Consignment Owner", owner.name, "phone"), "514 555-0100")

    # --- modification et annulation ----------------------------------------------------------------------------------

    def test_update_shows_before_and_after_writes_nothing_until_approval_then_can_be_undone(self):
        block = self._update()
        self.assertEqual(block["status"], "Proposed")
        self.assertEqual(self._rate(), 120.0)  # rien d'écrit à la proposition
        row = [r for r in block["rows"] if r.get("detail")][0]
        self.assertIn("120", row["detail"])
        self.assertIn("150", row["value"])
        self.assertTrue(block["reasoning"]["effects"])

        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        self.assertTrue(out["can_undo"])
        self.assertEqual(self._rate(), 150.5)
        [shown] = self.actions.refresh_blocks([block], self.operator)
        self.assertTrue(shown["can_undo"])

        undone = self.actions.undo(block["action_id"], COMPANY, self.operator)
        self.assertTrue(undone["ok"], undone)
        self.assertEqual(undone["status"], "Undone")
        self.assertEqual(self._rate(), 120.0)
        [shown] = self.actions.refresh_blocks([block], self.operator)
        self.assertEqual((shown["status"], shown["can_undo"]), ("Undone", False))
        with self.assertRaises(self.actions.ActionError):  # pas deux fois
            self.actions.undo(block["action_id"], COMPANY, self.operator)

        events = frappe.get_all(
            "Audit Event",
            filters={"entity_id": block["action_id"]},
            pluck="action",
        )
        self.assertIn("cortex.ai_action.executed", events)
        self.assertIn("cortex.ai_action.undone", events)

    def test_undo_is_refused_when_someone_changed_the_value_since(self):
        block = self._update()
        self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        frappe.db.set_value("Cortex Rental Item Profile", self.profile, "daily_rate", 199.0)
        out = self.actions.undo(block["action_id"], COMPANY, self.operator)
        self.assertFalse(out["ok"])
        self.assertEqual(out["status"], "Executed")
        self.assertTrue(out["can_undo"])
        self.assertIn("modifiée depuis", out["message"])
        self.assertEqual(self._rate(), 199.0)  # rien n'a été défait

    def test_a_value_changed_between_proposal_and_approval_makes_it_stale(self):
        block = self._update()
        frappe.db.set_value("Cortex Rental Item Profile", self.profile, "daily_rate", 130.0)
        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertFalse(out["ok"])
        self.assertEqual(out["status"], "Expired")
        self.assertEqual(self._rate(), 130.0)

    def test_only_the_requester_can_undo(self):
        block = self._update()
        self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        other = ensure_user("other-ops@cortex.test", ["Rental Manager"], COMPANY)
        frappe.set_user(other)
        with self.assertRaises(self.actions.ActionError):
            self.actions.undo(block["action_id"], COMPANY, other)
        with self.assertRaises(self.actions.ActionError):
            self.actions.undo(block["action_id"], OTHER, self.operator)

    def test_refused_inputs(self):
        cases = [
            {"fieldname": "company"},  # hors liste blanche
            {"fieldname": "category", "value": "Catégorie inventée"},  # hors des choix de la liste
            {"fieldname": "daily_rate", "value": "beaucoup"},
            {"fieldname": "daily_rate", "value": "-5"},
            {"fieldname": "daily_rate", "value": "120"},  # déjà cette valeur
            {"doctype": "User", "name": "Administrator", "fieldname": "first_name", "value": "x"},
            {"doctype": "Cortex AI Settings", "name": "Cortex AI Settings", "fieldname": "api_key", "value": "x"},
        ]
        for case in cases:
            with self.assertRaises(self.actions.ActionError, msg=str(case)):
                self._update(**case)
        with self.assertRaises(self.actions.ActionError):  # autre société
            self.actions.propose(
                "update_field",
                {
                    "doctype": "Cortex Rental Item Profile",
                    "name": self.profile,
                    "fieldname": "daily_rate",
                    "value": "99",
                },
                OTHER,
                self.operator,
            )
        self.assertEqual(self._rate(), 120.0)

    def test_the_reader_cannot_propose_or_approve_a_write(self):
        block = self._update()
        frappe.set_user(self.reader)
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose(
                "update_field",
                {
                    "doctype": "Cortex Rental Item Profile",
                    "name": self.profile,
                    "fieldname": "daily_rate",
                    "value": "99",
                },
                COMPANY,
                self.reader,
            )
        self.assertEqual(self._rate(), 120.0)
        self.assertEqual(block["status"], "Proposed")

    def test_customer_notes_and_checkbox_and_rental_state_guard(self):
        customer = ensure_customer(f"Client note {self.suffix}", COMPANY)
        block = self.actions.propose(
            "update_field",
            {"doctype": "Customer", "name": customer, "fieldname": "customer_details", "value": "Préfère le courriel."},
            COMPANY,
            self.operator,
        )
        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        self.assertEqual(frappe.db.get_value("Customer", customer, "customer_details"), "Préfère le courriel.")
        self.assertTrue(self.actions.undo(block["action_id"], COMPANY, self.operator)["ok"])
        self.assertFalse(frappe.db.get_value("Customer", customer, "customer_details"))

        flag = self.actions.propose(
            "update_field",
            {
                "doctype": "Cortex Rental Item Profile",
                "name": self.profile,
                "fieldname": "is_consignment_allowed",
                "value": "non",
            },
            COMPANY,
            self.operator,
        )
        self.assertTrue(self.actions.decide(flag["action_id"], True, COMPANY, self.operator)["ok"])
        self.assertEqual(frappe.db.get_value("Cortex Rental Item Profile", self.profile, "is_consignment_allowed"), 0)

        quote = self.actions.propose(
            "create_quote",
            {
                "customer": customer,
                "starts_at": "2026-12-02 09:00:00",
                "ends_at": "2026-12-04 18:00:00",
                "items": [{"item_code": self.code, "quantity": 1}],
            },
            COMPANY,
            self.operator,
        )
        tx = self.actions.decide(quote["action_id"], True, COMPANY, self.operator)["result_href"].rsplit("/", 1)[-1]
        note = {
            "doctype": "Cortex Rental Transaction",
            "name": tx,
            "fieldname": "notes",
            "value": "Livraison à l'entrepôt.",
        }
        self.assertTrue(
            self.actions.decide(
                self.actions.propose("update_field", note, COMPANY, self.operator)["action_id"],
                True,
                COMPANY,
                self.operator,
            )["ok"]
        )
        frappe.db.set_value("Cortex Rental Transaction", tx, "rental_state", "Contract")
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("update_field", {**note, "value": "Autre."}, COMPANY, self.operator)


if __name__ == "__main__":
    unittest.main()
