import unittest

from cortex_rental.services.consignment import ConsignmentService


class TestConsignmentSnapshotSanitization(unittest.TestCase):
    def test_unknown_top_level_key_is_dropped_by_the_allowlist(self):
        """
        Regression guard for the allowlist-first design: a field name
        that isn't on any denylist (because nobody has thought of it yet)
        must still be dropped, since only ALLOWED_SNAPSHOT_KEYS survive.
        """
        snapshot = ConsignmentService.sanitize_snapshot(
            {
                "serial_no": "SN-1",
                "gross_amount": 100.0,
                "some_future_field_nobody_denylisted_yet": "shipping_address_or_whatever",
            }
        )
        self.assertNotIn("some_future_field_nobody_denylisted_yet", snapshot)
        self.assertIn("serial_no", snapshot)

    def test_forbidden_key_nested_inside_metadata_is_stripped(self):
        snapshot = ConsignmentService.sanitize_snapshot(
            {
                "serial_no": "SN-1",
                "metadata": {"note": "ok", "customer_email": "leak@example.com"},
            }
        )
        self.assertNotIn("customer_email", snapshot["metadata"])
        self.assertEqual(snapshot["metadata"]["note"], "ok")

    def test_doctype_and_service_share_the_same_denylist(self):
        """
        Regression guard for the drift bug this fixes: the DocType-level
        backstop (consignment_payout.py) must use the exact same list as
        the service, not a second, independently maintained one.
        """
        from cortex_rental.cortex_rental.doctype.consignment_payout.consignment_payout import (
            ConsignmentService as ImportedFromDoctype,
        )

        self.assertIs(ImportedFromDoctype, ConsignmentService)


if __name__ == "__main__":
    unittest.main()
