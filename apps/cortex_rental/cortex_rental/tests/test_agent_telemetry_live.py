"""
Cortex Agent Run / Tool Call end-to-end regression suite. Requires a
live Frappe site (writes real DocTypes, checks a real permission
denial) — skipped in this sandbox. See test_multitenant_isolation.py
for the same pattern.
"""

import unittest
from types import SimpleNamespace

from cortex_rental.tests.live_fixtures import ensure_user

try:
    import frappe
except ImportError:
    frappe = None


@unittest.skipUnless(frappe, "requires a live Frappe site (bench) — not available in this sandbox")
class TestAgentTelemetryLive(unittest.TestCase):
    PLAIN_USER = "plain-user@cortex.test"
    AGENT_USER = "intake-agent@cortex.test"

    def setUp(self):
        # Hors requête HTTP, `frappe.local.request` n'existe pas : on lui donne des en-têtes vides, comme un vrai appel.
        frappe.local.request = SimpleNamespace(headers={}, method="POST", path="/test")
        # Une personne sans aucun rôle d'agent ni d'équipe : elle doit être refusée (et le refus journalisé).
        ensure_user(self.PLAIN_USER, [])
        # Un compte d'agent d'admission : il a le droit de lire le catalogue (portée « agent:items:read »).
        ensure_user(self.AGENT_USER, ["Agent Service Account", "Cortex Agent Intake"])

    def tearDown(self):
        frappe.set_user("Administrator")
        del frappe.local.request

    def test_successful_tool_call_creates_run_and_success_record(self):
        from cortex_rental.api.v1.items import search_items

        frappe.set_user(self.AGENT_USER)
        # Identifiant unique par exécution : une même demande rejouée incrémente le même enregistrement.
        self.request_id = "test-run-" + frappe.generate_hash(length=8)
        frappe.local.request.headers["X-Request-ID"] = self.request_id
        frappe.local.request.headers["X-Cortex-Agent-Id"] = "cortex_intake"

        search_items(query="")

        run = frappe.get_doc("Cortex Agent Run", {"request_id": self.request_id})
        self.assertEqual(run.agent_id, "cortex_intake")
        self.assertEqual(run.tool_call_count, 1)

        call = frappe.get_doc("Cortex Agent Tool Call", {"agent_run": run.name, "tool_name": "search_rental_items"})
        self.assertEqual(call.status, "Success")

    def test_denied_call_is_logged_and_flips_run_to_failed(self):
        from cortex_rental.api.v1.approvals import submit_approval

        frappe.set_user(self.PLAIN_USER)
        self.request_id = "test-run-" + frappe.generate_hash(length=8)
        frappe.local.request.headers["X-Request-ID"] = self.request_id
        # Assumes the current test user does not hold a role in
        # SCOPE_ROLE_MAP["agent:approval:submit"] nor HUMAN_STAFF_ROLES.
        with self.assertRaises(frappe.PermissionError):
            submit_approval()

        run = frappe.get_doc("Cortex Agent Run", {"request_id": self.request_id})
        self.assertEqual(run.status, "Failed")

        call = frappe.get_doc("Cortex Agent Tool Call", {"agent_run": run.name, "tool_name": "submit_approval_request"})
        self.assertEqual(call.status, "Denied")
        self.assertIn("portée", call.error_message.lower())  # message en français (la portée exigée est nommée)


if __name__ == "__main__":
    unittest.main()
