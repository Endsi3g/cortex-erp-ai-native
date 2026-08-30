"""
Cortex Agent Run / Tool Call end-to-end regression suite. Requires a
live Frappe site (writes real DocTypes, checks a real permission
denial) — skipped in this sandbox. See test_multitenant_isolation.py
for the same pattern.
"""

import unittest

try:
    import frappe
except ImportError:
    frappe = None


@unittest.skipUnless(frappe, "requires a live Frappe site (bench) — not available in this sandbox")
class TestAgentTelemetryLive(unittest.TestCase):
    def test_successful_tool_call_creates_run_and_success_record(self):
        from cortex_rental.api.v1.items import search_items

        frappe.local.request.headers["X-Request-ID"] = "test-run-001"
        frappe.local.request.headers["X-Cortex-Agent-Id"] = "cortex_intake"

        search_items(query="")

        run = frappe.get_doc("Cortex Agent Run", {"request_id": "test-run-001"})
        self.assertEqual(run.agent_id, "cortex_intake")
        self.assertEqual(run.tool_call_count, 1)

        call = frappe.get_doc("Cortex Agent Tool Call", {"agent_run": run.name, "tool_name": "search_rental_items"})
        self.assertEqual(call.status, "Success")

    def test_denied_call_is_logged_and_flips_run_to_failed(self):
        from cortex_rental.api.v1.approvals import submit_approval

        frappe.local.request.headers["X-Request-ID"] = "test-run-002"
        # Assumes the current test user does not hold a role in
        # SCOPE_ROLE_MAP["agent:approval:submit"] nor HUMAN_STAFF_ROLES.
        with self.assertRaises(frappe.PermissionError):
            submit_approval()

        run = frappe.get_doc("Cortex Agent Run", {"request_id": "test-run-002"})
        self.assertEqual(run.status, "Failed")

        call = frappe.get_doc("Cortex Agent Tool Call", {"agent_run": run.name, "tool_name": "submit_approval_request"})
        self.assertEqual(call.status, "Denied")
        self.assertIn("scope", call.error_message.lower())


if __name__ == "__main__":
    unittest.main()
