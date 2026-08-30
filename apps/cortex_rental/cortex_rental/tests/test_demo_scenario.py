import unittest
from cortex_rental.services.pricing import PricingService
from cortex_rental.services.transaction_state import TransactionStateService
from cortex_rental.api.v1.quotes import create_draft_handler, preview_pricing_handler
from cortex_rental.api.v1.availability import check_availability_handler, get_matrix_handler
from cortex_rental.api.v1.approvals import submit_approval_handler
from cortex_rental.api.v1.consignment import prepare_owner_statement_handler
from cortex_rental.cortex_rental.doctype.approval_request.approval_request import ApprovalRequest
from cortex_rental.cortex_rental.doctype.audit_event.audit_event import AuditEvent


class TestCortexDemoScenario(unittest.TestCase):
    def setUp(self):
        self.company = "CineRental Montreal"
        self.customer = "Dune 3 Productions Inc."
        self.starts_at = "2026-09-01T09:00:00Z"
        self.ends_at = "2026-09-08T09:00:00Z"  # 7 calendar days

    def test_step_1_and_2_agent_creates_quote_draft(self):
        payload = {
            "customer_id": "cust-dune3-01",
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "lines": [{"item_id": "itm-alexa-35-pkg", "quantity": 3, "unit_rate": 1500.00}],
            "evidence_ids": ["ev-email-001"],
            "notes": "Incoming request from Dune 3 Productions for 3x Alexa 35 Packages.",
        }

        result = create_draft_handler(payload, self.company, "agent:cortex-intake")
        self.assertEqual(result["state"], "quote")
        self.assertEqual(result["calendar_days"], 7)
        self.assertEqual(result["billable_days"], 3.0)
        # 3 items * 1500 rate * 3 billable days = 13,500.00
        self.assertEqual(result["total"], "13500.00")
        self.assertFalse(result["customer_account_ready"])
        self.assertFalse(result["insurance_ready"])
        self.assertFalse(result["payment_ready"])

    def test_preview_pricing_matches_create_draft_math_without_persisting(self):
        # Same inputs, same PricingService calls as
        # test_step_1_and_2_agent_creates_quote_draft above — preview_pricing
        # must compute the identical total, since the Transaction
        # Composer's live preview has to agree with what create_quote_draft
        # actually charges once submitted.
        payload = {
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "lines": [{"item_id": "itm-alexa-35-pkg", "quantity": 3, "unit_rate": 1500.00}],
        }
        result = preview_pricing_handler(payload, self.company)
        self.assertEqual(result["calendar_days"], 7)
        self.assertEqual(result["billable_days"], 3.0)
        self.assertEqual(result["total"], "13500.00")

    def test_preview_pricing_requires_date_window(self):
        with self.assertRaises(ValueError):
            preview_pricing_handler({"starts_at": self.starts_at}, self.company)

    def test_preview_pricing_missing_unit_rate_defaults_to_zero_not_fabricated_rate(self):
        # create_draft_handler defaults a missing unit_rate to 100.0 (a
        # pre-existing behavior, not changed here) — preview_pricing
        # deliberately does not inherit that: a live preview silently
        # showing a fake $100/day rate would be worse than an honest $0.
        payload = {
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "lines": [{"item_id": "itm-no-rate-set", "quantity": 1}],
        }
        result = preview_pricing_handler(payload, self.company)
        self.assertEqual(result["total"], "0.00")
        self.assertEqual(result["lines"][0]["unit_rate"], 0.0)

    def test_step_4_availability_check(self):
        payload = {
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "items": [{"item_id": "itm-alexa-35-pkg", "quantity": 3}],
        }
        results = check_availability_handler(payload, self.company)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["is_available"])
        self.assertEqual(results[0]["available_quantity"], 10.0)

    def test_availability_matrix_requires_date_window(self):
        with self.assertRaises(ValueError):
            get_matrix_handler({"starts_at": self.starts_at}, self.company)

    def test_availability_matrix_no_frappe_returns_labeled_mock(self):
        # In this sandbox `frappe` is unimportable, so get_matrix_handler
        # takes its documented mocked branch (same contract as
        # AvailabilityService.check without a live DB) rather than
        # silently fabricating a real-looking grid.
        result = get_matrix_handler({"starts_at": self.starts_at, "ends_at": self.ends_at}, self.company)
        self.assertEqual(result["items"], [])
        self.assertIn("Mocked result", result["notes"])

    def test_step_6_pricing_rule_7d_equals_3d(self):
        calendar_days, billable_days = PricingService.compute_billable_days("2026-09-01", "2026-09-08", self.company)
        self.assertEqual(calendar_days, 7)
        self.assertEqual(billable_days, 3.0)

    def test_step_7_agent_submits_approval_request(self):
        payload = {
            "action": "rental.quote.transition_to_reservation",
            "entity_type": "Cortex Rental Transaction",
            "entity_id": "CR-TRX-2026-00001",
            "proposed_payload": {"rental_state": "Reservation"},
            "evidence_ids": ["ev-email-001"],
            "rationale": "Client confirmed quote by email, requesting reservation hold.",
        }
        result = submit_approval_handler(payload, self.company, "agent:cortex-intake")
        self.assertEqual(result["status"], "Pending")
        self.assertEqual(result["action"], "rental.quote.transition_to_reservation")

    def test_security_gate_agent_cannot_transition_to_reservation_autonomously(self):
        allowed, reason = TransactionStateService.can_transition(
            current_state="Quote", target_state="Reservation", transaction_doc=None, is_agent=True
        )
        self.assertFalse(allowed)
        self.assertIn("Approval required", reason)

    def test_step_9_consignment_payout_redacts_renter_identity(self):
        payout = prepare_owner_statement_handler(
            {
                "owner_id": "Roger Deakins Productions Inc.",
                "gross_amount": 9000.00,
                "consignment_percentage": 70.0,
                "serial_no": "SN-ALX35-001",
                "days": 3.0,
                "rate": 1500.00,
                "customer_name": "Dune 3 Productions Inc.",
                "customer_email": "producer@dune3.com",
            },
            self.company,
        )

        self.assertEqual(payout["owner_payout_amount"], 6300.00)
        snapshot = payout["calculation_snapshot"]
        self.assertEqual(snapshot["serial_no"], "SN-ALX35-001")
        self.assertEqual(snapshot["payout_amount"], 6300.00)
        # Verify confidentiality: no renter keys in snapshot
        self.assertNotIn("customer_name", snapshot)
        self.assertNotIn("customer_email", snapshot)
        self.assertNotIn("Dune 3 Productions", str(snapshot))

    def test_step_7b_approval_resolves_target_state_from_proposed_payload(self):
        req = ApprovalRequest()
        req.action = "rental.quote.transition_to_reservation"
        req.proposed_payload = {"rental_state": "Reservation"}
        self.assertEqual(req._resolve_target_rental_state(), "Reservation")

    def test_step_7c_approval_resolves_target_state_from_action_name_fallback(self):
        req = ApprovalRequest()
        req.action = "rental.quote.transition_to_checked_out"
        req.proposed_payload = None
        self.assertEqual(req._resolve_target_rental_state(), "Checked Out")

    def test_audit_event_immutability(self):
        event = AuditEvent()
        event.name = "AUDIT-001"
        event.is_new = lambda: False
        with self.assertRaises(PermissionError):
            event.before_save()
        with self.assertRaises(PermissionError):
            event.on_trash()


if __name__ == "__main__":
    unittest.main()
