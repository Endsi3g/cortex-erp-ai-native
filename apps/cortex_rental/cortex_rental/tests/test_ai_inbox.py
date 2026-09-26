"""AI Inbox aggregation on the fake frappe."""

import json
import unittest

from cortex_rental.tests.fake_frappe import fake_frappe, load

AI = "cortex_rental.api.v1.ai"


class TestInbox(unittest.TestCase):
    def _seed(self, frappe, confidence=0.62, validation="Valid"):
        frappe.tables["Approval Request"] = [
            {
                "name": "APPR-1",
                "company": "A",
                "status": "Pending",
                "action": "rental.transaction.transition_to_contract",
                "entity_type": "Cortex Rental Transaction",
                "entity_id": "CR-1",
                "requested_by_type": "Agent",
                "requested_by_id": "agent:intake",
                "creation": "2026-09-25 10:00:00",
                "rationale": "COI reçu",
            },
        ]
        frappe.tables["Cortex Rental Transaction"] = [
            {"name": "CR-1", "company": "A", "customer": "C1", "rental_state": "Quote", "grand_total": 100}
        ]
        frappe.tables["Customer"] = [{"name": "C1", "customer_name": "Dune"}]
        frappe.tables["Cortex Inbound Request"] = [
            {
                "name": "INB-1",
                "company": "A",
                "source_channel": "Email",
                "sender_email": "a@b.c",
                "subject": "Besoin Alexa",
                "status": "Received",
                "creation": "2026-09-25 09:00:00",
                "extracted_transaction": None,
            },
        ]
        payload = {
            "customer": {"name": "Paul", "email": "p@x.c"},
            "rental_period": {"starts_at": "x"},
            "items": [{"raw_text": "Alexa"}],
        }
        frappe.tables["Cortex Extraction Run"] = [
            {
                "name": "XTR-1",
                "company": "A",
                "inbound_request": "INB-1",
                "extracted_payload": json.dumps(payload),
                "validation_status": validation,
                "overall_confidence": confidence,
                "review_required": 1,
                "actor_id": "agent:intake",
                "extracted_at": "2026-09-25 09:01:00",
            },
        ]
        frappe.tables["Audit Event"] = [
            {
                "company": "A",
                "actor_type": "Agent",
                "action": "cortex.rental_transaction.draft_created",
                "entity_type": "Cortex Rental Transaction",
                "entity_id": "CR-1",
                "actor_id": "agent:intake",
                "creation": "2026-09-25 08:00:00",
            },
        ]

    def test_approvals_only_for_approvers(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            ai = load(AI)
            kinds = {row["kind"] for row in ai.list_inbox_handler("A", None, False, {"Rental Operator"})}
            self.assertNotIn("approval", kinds)
            kinds = {row["kind"] for row in ai.list_inbox_handler("A", None, False, {"Rental Manager"})}
            self.assertEqual(kinds, {"approval", "inbound", "draft"})

    def test_inbound_state_and_missing_fields_come_from_the_extraction(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            row = next(r for r in load(AI).list_inbox_handler("A", "inbound", False, set()) if r["kind"] == "inbound")
            self.assertEqual(row["state"], "low_confidence")
            self.assertEqual(row["confidence"], 0.62)
            self.assertIn("rental_period.ends_at", row["summary"])
            self.assertIn("items[0].match", row["summary"])

    def test_invalid_extraction_is_an_error_state(self):
        with fake_frappe() as frappe:
            self._seed(frappe, confidence=0.95, validation="Invalid")
            row = load(AI).list_inbox_handler("A", "inbound", False, set())[0]
            self.assertEqual(row["state"], "extraction_error")

    def test_missing_confidence_stays_unknown(self):
        with fake_frappe() as frappe:
            self._seed(frappe, confidence=None)
            row = load(AI).list_inbox_handler("A", "inbound", False, set())[0]
            self.assertIsNone(row["confidence"])
            self.assertEqual(row["state"], "needs_review")

    def test_agent_draft_is_listed_with_customer(self):
        with fake_frappe() as frappe:
            self._seed(frappe)
            row = load(AI).list_inbox_handler("A", "draft", False, set())[0]
            self.assertEqual((row["source_id"], row["customer"], row["agent"]), ("CR-1", "Dune", "agent:intake"))


if __name__ == "__main__":
    unittest.main()
