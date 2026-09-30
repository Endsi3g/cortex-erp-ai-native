"""Écritures comptables : équilibre, plan de comptes et immuabilité (sans banc Frappe)."""

import json
import os
import unittest

from cortex_rental.services import ledger

MODULE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cortex_rental")


def load(*parts):
    with open(os.path.join(MODULE_DIR, *parts), encoding="utf-8") as handle:
        return json.load(handle)


class Doc:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class TestAccounts(unittest.TestCase):
    def test_account_format_number_dash_name(self):
        self.assertEqual(ledger.split_account("2310 - TPS à remettre"), ("2310", "TPS à remettre"))

    def test_every_account_has_a_default(self):
        self.assertEqual(set(ledger.DEFAULT_ACCOUNTS), set(ledger.SETTING_FIELDS))

    def test_the_company_can_change_its_chart_of_accounts(self):
        names = {
            f["fieldname"] for f in load("doctype", "cortex_finance_settings", "cortex_finance_settings.json")["fields"]
        }
        self.assertTrue(set(ledger.SETTING_FIELDS.values()) <= names)


class TestBalance(unittest.TestCase):
    def test_final_invoice_entry_balances_with_deposit_applied(self):
        # location 1 000 $ + 100 $ de retard, acompte 300 $ : net 800 $, taxes 14,975 % sur le net
        net = 800.0
        tps, tvq = round(net * 0.05, 2), round(net * 0.09975, 2)
        total = net + tps + tvq
        lines = [
            ("receivable", total, 0),
            ("deposits", 300.0, 0),
            ("revenue", 0, 1000.0),
            ("late_fees", 0, 100.0),
            ("tps", 0, tps),
            ("tvq", 0, tvq),
        ]
        self.assertTrue(ledger.is_balanced(lines))

    def test_unbalanced_entry_is_detected(self):
        self.assertFalse(ledger.is_balanced([("cash", 100.0, 0), ("receivable", 0, 99.0)]))

    def test_payment_and_refund_are_mirror_images(self):
        pay = [("cash", 50.0, 0), ("receivable", 0, 50.0)]
        refund = [("receivable", 50.0, 0), ("cash", 0, 50.0)]
        self.assertTrue(ledger.is_balanced(pay) and ledger.is_balanced(refund))


class TestImmutability(unittest.TestCase):
    def test_entries_cannot_be_edited_or_deleted_by_any_role(self):
        doc = load("doctype", "cortex_journal_entry", "cortex_journal_entry.json")
        for perm in doc["permissions"]:
            self.assertFalse(perm.get("write") or perm.get("delete"), perm["role"])

    def test_entries_are_company_scoped(self):
        from cortex_rental import hooks

        self.assertIn("Cortex Journal Entry", hooks.permission_query_conditions)

    def test_invoice_lines_are_tagged_so_the_ledger_never_guesses_from_text(self):
        names = {
            f["fieldname"]
            for f in load("doctype", "cortex_rental_invoice_line", "cortex_rental_invoice_line.json")["fields"]
        }
        self.assertIn("line_kind", names)


if __name__ == "__main__":
    unittest.main()
