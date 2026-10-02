"""Facturation : taxes, réglages par société, droits et vues financières (sans banc Frappe)."""

import glob
import json
import os
import unittest

from cortex_rental.services import billing

MODULE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cortex_rental")


def load(*parts):
    with open(os.path.join(MODULE_DIR, *parts), encoding="utf-8") as handle:
        return json.load(handle)


class TestTaxes(unittest.TestCase):
    def test_quebec_taxes_are_computed_on_the_subtotal_not_compounded(self):
        tps, tvq = billing.compute_taxes(1000.0, billing.DEFAULTS)
        self.assertEqual((tps, tvq), (50.0, 99.75))

    def test_rounding_to_the_cent(self):
        tps, tvq = billing.compute_taxes(33.33, billing.DEFAULTS)
        self.assertEqual((tps, tvq), (1.67, 3.32))

    def test_a_company_without_tax_numbers_can_switch_taxes_off(self):
        settings = {**billing.DEFAULTS, "apply_taxes": 0}
        self.assertEqual(billing.compute_taxes(500, settings), (0.0, 0.0))
        self.assertEqual(billing.combined_rate(settings), 0.0)

    def test_combined_rate(self):
        self.assertEqual(billing.combined_rate(billing.DEFAULTS), 14.975)

    def test_late_fee_is_off_until_the_company_decides(self):
        self.assertEqual(billing.DEFAULTS["late_fee_enabled"], 0)

    def test_deposit_is_a_company_setting(self):
        self.assertGreater(billing.DEFAULTS["deposit_percent"], 0)


class TestFinanceDoctypes(unittest.TestCase):
    def test_settings_are_one_per_company(self):
        doc = load("doctype", "cortex_finance_settings", "cortex_finance_settings.json")
        self.assertEqual(doc["autoname"], "field:company")
        self.assertTrue(next(f for f in doc["fields"] if f["fieldname"] == "company")["unique"])

    def test_invoices_and_payments_cannot_be_deleted_or_edited_by_anyone(self):
        for name in ("cortex_rental_invoice", "cortex_rental_payment"):
            doc = load("doctype", name, f"{name}.json")
            for perm in doc["permissions"]:
                self.assertFalse(perm.get("delete"), f"{name}:{perm['role']}")

    def test_payments_are_create_only(self):
        doc = load("doctype", "cortex_rental_payment", "cortex_rental_payment.json")
        self.assertTrue(all(not p.get("write") for p in doc["permissions"]))
        roles = {p["role"] for p in doc["permissions"] if p.get("create")}
        self.assertTrue({"Cortex Finance Manager", "Cortex Counter Staff", "Rental Manager"} <= roles)

    def test_invoices_are_linked_from_the_rental_form(self):
        doc = load("doctype", "cortex_rental_transaction", "cortex_rental_transaction.json")
        self.assertIn("Cortex Rental Invoice", {link["link_doctype"] for link in doc["links"]})
        names = {f["fieldname"] for f in doc["fields"]}
        self.assertTrue({"tps_amount", "tvq_amount"} <= names)

    def test_every_finance_doctype_is_company_scoped(self):
        from cortex_rental import hooks

        for doctype in ("Cortex Rental Invoice", "Cortex Rental Payment", "Cortex Finance Settings"):
            self.assertIn(doctype, hooks.permission_query_conditions)


class TestFinanceViews(unittest.TestCase):
    def test_finance_workspace_uses_cortex_records_not_erpnext_accounting(self):
        workspace = load("workspace", "cortex_finance", "cortex_finance.json")
        targets = {s["link_to"] for s in workspace["shortcuts"]}
        self.assertFalse(targets & {"Sales Invoice", "Payment Entry", "General Ledger", "Profit and Loss Statement"})
        self.assertIn("Cortex Rental Invoice", targets)
        self.assertIn("Cortex Finance Settings", targets)

    def test_finance_number_cards_read_cortex_doctypes(self):
        for path in glob.glob(os.path.join(MODULE_DIR, "number_card", "*", "*.json")):
            with open(path, encoding="utf-8") as handle:
                card = json.load(handle)
            if card["label"] in ("Facturé ce mois", "Encaissé ce mois", "Solde à recevoir", "Factures en retard"):
                self.assertIn(card["document_type"], ("Cortex Rental Invoice", "Cortex Rental Payment"), path)

    def test_overdue_card_is_the_only_red_finance_card(self):
        colors = {}
        for path in glob.glob(os.path.join(MODULE_DIR, "number_card", "*", "*.json")):
            with open(path, encoding="utf-8") as handle:
                card = json.load(handle)
            colors[card["label"]] = card.get("color") or ""
        self.assertEqual(colors["Facturé ce mois"], "")
        self.assertNotEqual(colors["Factures en retard"], "")


if __name__ == "__main__":
    unittest.main()
