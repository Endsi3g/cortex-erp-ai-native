"""
Multi-tenant isolation regression suite.

These tests require a live Frappe site (they create real Companies, Users,
User Permissions and documents) and are skipped when `frappe` is not
importable — which is the case in this repository's lightweight
sandbox/CI environment (see apps/cortex_rental/pyproject.toml — no bench
is provisioned here). They are written now so that the very first `bench
--site <site> run-tests --app cortex_rental` on a real bench proves the
tenant-isolation fixes in permissions/agent_scopes.py and
permissions/__init__.py actually hold, rather than relying on manual QA.

Run for real with, e.g.:
    bench --site cortex.localhost run-tests --app cortex_rental \\
        --module cortex_rental.tests.test_multitenant_isolation
"""

import unittest

try:
    import frappe
except ImportError:
    frappe = None


@unittest.skipUnless(frappe, "requires a live Frappe site (bench) — not available in this sandbox")
class TestMultiTenantIsolation(unittest.TestCase):
    COMPANY_A = "Cortex Test Co A"
    COMPANY_B = "Cortex Test Co B"

    @classmethod
    def setUpClass(cls):
        for company, abbr in ((cls.COMPANY_A, "CTA"), (cls.COMPANY_B, "CTB")):
            if not frappe.db.exists("Company", company):
                frappe.get_doc(
                    {"doctype": "Company", "company_name": company, "abbr": abbr, "default_currency": "USD"}
                ).insert(ignore_permissions=True)

        cls.user_a = "tenant-a-agent@cortex.test"
        if not frappe.db.exists("User", cls.user_a):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": cls.user_a,
                    "first_name": "Tenant A Agent",
                    "send_welcome_email": 0,
                    "roles": [{"role": "Agent Service Account"}, {"role": "Cortex Agent Reporting"}],
                }
            ).insert(ignore_permissions=True)
            frappe.get_doc(
                {"doctype": "User Permission", "user": cls.user_a, "allow": "Company", "for_value": cls.COMPANY_A}
            ).insert(ignore_permissions=True)

        cls.audit_a = frappe.get_doc(
            {
                "doctype": "Audit Event",
                "company": cls.COMPANY_A,
                "actor_type": "Agent",
                "actor_id": cls.user_a,
                "action": "test.tenant_a_event",
                "entity_type": "Test",
                "entity_id": "TEST-A-1",
            }
        )
        cls.audit_a.flags.ignore_permissions = True
        cls.audit_a.insert()

        cls.audit_b = frappe.get_doc(
            {
                "doctype": "Audit Event",
                "company": cls.COMPANY_B,
                "actor_type": "Agent",
                "actor_id": "system",
                "action": "test.tenant_b_event",
                "entity_type": "Test",
                "entity_id": "TEST-B-1",
            }
        )
        cls.audit_b.flags.ignore_permissions = True
        cls.audit_b.insert()

    def setUp(self):
        frappe.set_user(self.user_a)

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_agent_scoped_to_company_a_cannot_list_company_b_audit_events(self):
        names = frappe.get_all("Audit Event", filters={"entity_id": "TEST-B-1"}, pluck="name")
        self.assertEqual(names, [], "Company B audit event must not be visible to a Company A-scoped identity")

    def test_agent_scoped_to_company_a_can_list_its_own_audit_events(self):
        names = frappe.get_all("Audit Event", filters={"entity_id": "TEST-A-1"}, pluck="name")
        self.assertEqual(names, [self.audit_a.name])

    def test_agent_cannot_read_company_b_audit_event_by_direct_get(self):
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("Audit Event", self.audit_b.name).check_permission("read")

    def test_get_company_context_rejects_unauthorized_company_header(self):
        from cortex_rental.permissions.agent_scopes import get_company_context

        with self.assertRaises(frappe.PermissionError):
            get_company_context(self.COMPANY_B)

    def test_get_company_context_accepts_authorized_company_header(self):
        from cortex_rental.permissions.agent_scopes import get_company_context

        self.assertEqual(get_company_context(self.COMPANY_A), self.COMPANY_A)


if __name__ == "__main__":
    unittest.main()
