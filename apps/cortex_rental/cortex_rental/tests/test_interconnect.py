"""Fonctions interconnectées : rappels, frais de dommages, fiche client 360°, outils de l'assistant (contrat de code)."""

import json
import os
import unittest

BASE = os.path.dirname(os.path.dirname(__file__))


def read(*parts):
    with open(os.path.join(BASE, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestReminders(unittest.TestCase):
    def test_the_scheduler_runs_reminders_every_hour(self):
        self.assertIn('"hourly": ["cortex_rental.services.reminders.hourly"]', read("hooks.py"))

    def test_reminders_are_deduplicated_over_24_hours_and_never_write_to_records(self):
        src = read("services", "reminders.py")
        self.assertIn("hours=-24", src)
        self.assertNotIn(".save(", src)
        self.assertNotIn("rental_state", src.split("def _notify")[1].split("def holds_expiring")[0])


class TestDamageBilling(unittest.TestCase):
    def test_damage_billing_is_off_by_default_and_needs_the_setting(self):
        src = read("services", "billing.py")
        self.assertIn('"damage_billing_enabled": 0', src.replace("'", '"'))
        self.assertIn('if not settings.get("damage_billing_enabled")', src)

    def test_damage_lines_are_posted_to_their_own_ledger_account(self):
        src = read("services", "ledger.py")
        self.assertIn('("damages", 0, by_kind.get("Damage", 0.0))', src)
        self.assertIn("4200 - Dommages et pertes facturés", src)

    def test_invoice_line_kind_accepts_damage(self):
        path = os.path.join(
            BASE, "cortex_rental", "doctype", "cortex_rental_invoice_line", "cortex_rental_invoice_line.json"
        )
        fields = {f["fieldname"]: f for f in json.load(open(path, encoding="utf-8"))["fields"]}
        self.assertIn("Damage", fields["line_kind"]["options"].split("\n"))


class TestCustomer360(unittest.TestCase):
    def test_the_summary_is_company_scoped_and_permission_checked(self):
        src = read("services", "customer_360.py")
        self.assertIn('"cortex_company": company', src)
        self.assertIn('frappe.has_permission("Customer", "read", customer)', src)
        self.assertIn('frappe.has_permission("Cortex Rental Invoice", "read")', src)

    def test_no_score_or_risk_is_invented(self):
        src = read("services", "customer_360.py").lower()
        for word in ("score", "risk", "risque", "cote"):
            self.assertNotIn(word, src)

    def test_the_customer_form_script_is_registered(self):
        self.assertIn('"Customer": "public/js/cortex_customer.js"', read("hooks.py"))
        self.assertIn("customers.summary", read("public", "js", "cortex_customer.js"))

    def test_the_endpoint_requires_a_human_staff_role(self):
        body = read("api", "v1", "customers.py").split("def summary")[1].split("@frappe.whitelist")[0]
        self.assertIn("require_human_staff_role()", body)


class TestAssistantReadTools(unittest.TestCase):
    def test_new_tools_are_read_only_and_granted_only_to_operations_and_returns(self):
        tools = read("services", "ai", "tools.py")
        for name in ("customer_summary", "late_returns"):
            body = tools.split(f"def {name}")[1].split("\n@tool(")[0]
            for write in (".insert(", ".save(", ".submit(", "set_value", "delete"):
                self.assertNotIn(write, body)
        policy = read("services", "tool_policy.py")
        self.assertIn('"cortex-returns": ["list_rentals", "late_returns"]', policy)
        self.assertNotIn("customer_summary", policy.split('"cortex-availability"')[1].split('"cortex-consignment"')[0])


class TestFleetUtilizationReport(unittest.TestCase):
    def test_the_report_is_on_the_catalog_workspace(self):
        path = os.path.join(BASE, "cortex_rental", "workspace", "cortex_catalog", "cortex_catalog.json")
        data = json.load(open(path, encoding="utf-8"))
        self.assertIn("Utilisation du parc", [s["link_to"] for s in data["shortcuts"]])
        self.assertIn("Utilisation du parc", [l.get("link_to") for l in data["links"]])
        self.assertIn("Utilisation du parc", read("public", "js", "cortex_nav.js"))
