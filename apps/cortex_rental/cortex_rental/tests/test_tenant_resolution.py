"""
Tenant resolution on the real (`if frappe:`) code path, via the in-memory
fake. Regression cover for the fallback that used to hand every identity
without a Company permission the hard-coded "CineRental Montreal", and for
the user-editable session default that could pick any Company.
"""

import unittest

from cortex_rental.tests.fake_frappe import fake_frappe, load

SCOPES = "cortex_rental.permissions.agent_scopes"


class TestAllowedCompanies(unittest.TestCase):
    def test_user_permission_grants_only_listed_companies(self):
        with fake_frappe(user="ops@a", roles=["Rental Operator"]) as frappe:
            frappe.tables["Company"] = [{"name": "A"}, {"name": "B"}]
            frappe.tables["User Permission"] = [{"user": "ops@a", "allow": "Company", "for_value": "A"}]
            self.assertEqual(load(SCOPES).get_allowed_companies(), ["A"])

    def test_no_permission_on_multi_company_site_grants_nothing(self):
        with fake_frappe(user="ops@x", roles=["Rental Operator"]) as frappe:
            frappe.tables["Company"] = [{"name": "A"}, {"name": "B"}]
            frappe.tables["User Permission"] = []
            self.assertEqual(load(SCOPES).get_allowed_companies(), [])

    def test_single_company_site_grants_that_company(self):
        with fake_frappe(user="ops@x", roles=["Rental Operator"]) as frappe:
            frappe.tables["Company"] = [{"name": "Only"}]
            frappe.tables["User Permission"] = []
            self.assertEqual(load(SCOPES).get_allowed_companies(), ["Only"])

    def test_system_manager_sees_every_company(self):
        with fake_frappe(user="admin@x", roles=["System Manager"]) as frappe:
            frappe.tables["Company"] = [{"name": "A"}, {"name": "B"}]
            self.assertEqual(load(SCOPES).get_allowed_companies(), ["A", "B"])

    def test_no_company_table_grants_nothing(self):
        with fake_frappe(user="ops@x", roles=["Rental Operator"]):
            self.assertEqual(load(SCOPES).get_allowed_companies(), [])


class TestCompanyContext(unittest.TestCase):
    def test_header_outside_allowed_set_is_refused(self):
        with fake_frappe(user="ops@a", roles=["Rental Operator"]) as frappe:
            frappe.tables["Company"] = [{"name": "A"}, {"name": "B"}]
            frappe.tables["User Permission"] = [{"user": "ops@a", "allow": "Company", "for_value": "A"}]
            scopes = load(SCOPES)
            with self.assertRaises(frappe.PermissionError):
                scopes.get_company_context("B")

    def test_identity_without_company_is_refused(self):
        with fake_frappe(user="ops@x", roles=["Rental Operator"]) as frappe:
            frappe.tables["Company"] = [{"name": "A"}, {"name": "B"}]
            scopes = load(SCOPES)
            with self.assertRaises(frappe.PermissionError):
                scopes.get_company_context("A")

    def test_single_allowed_company_needs_no_header(self):
        with fake_frappe(user="ops@a", roles=["Rental Operator"]) as frappe:
            frappe.tables["Company"] = [{"name": "A"}, {"name": "B"}]
            frappe.tables["User Permission"] = [{"user": "ops@a", "allow": "Company", "for_value": "A"}]
            self.assertEqual(load(SCOPES).get_company_context(None), "A")


class TestSchemaStrictFake(unittest.TestCase):
    """The fake itself must reject what bench would reject."""

    def test_unknown_field_is_rejected(self):
        with fake_frappe() as frappe:
            doc = frappe.get_doc(
                {
                    "doctype": "Rental Pricing Rule",
                    "company": "A",
                    "rule_name": "x",
                    "calendar_days": 7,
                    "billable_days": 3,
                    "not_a_field": 1,
                }
            )
            with self.assertRaises(frappe.ValidationError):
                doc.insert()

    def test_missing_mandatory_field_is_rejected(self):
        with fake_frappe() as frappe:
            doc = frappe.get_doc(
                {"doctype": "Rental Pricing Rule", "company": "A", "calendar_days": 7, "billable_days": 3}
            )
            with self.assertRaises(frappe.ValidationError):
                doc.insert()


if __name__ == "__main__":
    unittest.main()
