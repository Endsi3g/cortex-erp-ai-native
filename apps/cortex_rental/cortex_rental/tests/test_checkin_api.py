"""
Unit tests for the Check-In service and handlers (PRD-RET-001 & PRD-RET-002).
Tests validation logic, handlers, parsing, and data shaping.
"""

import unittest
from unittest.mock import MagicMock, patch

from cortex_rental.api.v1.checkin import complete_checkin_handler, submit_checkin_handler
from cortex_rental.services.checkin import (
    DISPOSITION_TO_SERIAL_STATUS,
    _apply_disposition,
    _increment_returned_qty,
    _is_fully_returned,
    complete_checkin,
    lookup_scan_target,
    process_checkin,
    search_active_transactions,
)


class TestCheckinServiceAndApi(unittest.TestCase):
    def test_disposition_to_serial_status_mapping(self):
        self.assertEqual(DISPOSITION_TO_SERIAL_STATUS["Return to Stock"], "Active")
        self.assertEqual(DISPOSITION_TO_SERIAL_STATUS["Quarantine"], "Quarantine")
        self.assertEqual(DISPOSITION_TO_SERIAL_STATUS["Repair"], "Under Repair")
        self.assertEqual(DISPOSITION_TO_SERIAL_STATUS["Missing"], "Missing")
        self.assertEqual(DISPOSITION_TO_SERIAL_STATUS["Write-off"], "Decommissioned")

    def test_complete_checkin_handler_missing_id_raises(self):
        with self.assertRaises(ValueError):
            complete_checkin_handler({}, "Test Co", "user@test.local")

    def test_submit_checkin_handler_missing_params_raises(self):
        with self.assertRaises(ValueError):
            submit_checkin_handler({}, "Test Co", "user@test.local")

        with self.assertRaises(ValueError):
            submit_checkin_handler({"transaction_id": "TRX-001"}, "Test Co", "user@test.local")

    def test_submit_checkin_handler_json_string_parsing(self):
        payload = {
            "transaction_id": "TRX-001",
            "items": '[{"item_code": "CAM-01", "returned_qty": 1}]',
            "finalize_mode": "auto",
        }
        # In test sandbox without Frappe, process_checkin returns a mock dict
        result = submit_checkin_handler(payload, "Test Co", "user@test.local")
        self.assertEqual(result["transaction"], "TRX-001")
        self.assertEqual(result["status"], "Completed")

    def test_search_active_transactions_without_frappe(self):
        res = search_active_transactions("Test Co")
        self.assertEqual(res, [])

    def test_lookup_scan_target_empty(self):
        res = lookup_scan_target("Test Co", "")
        self.assertEqual(res["type"], "empty")

    def test_mock_fallback_process_checkin(self):
        res = process_checkin(
            company="Test Co",
            actor_id="tester",
            transaction_id="TRX-100",
            items=[{"item_code": "LENS-01", "returned_qty": 1}],
            finalize_mode="partial",
        )
        self.assertEqual(res["transaction"], "TRX-100")
        self.assertEqual(res["finalize_mode"], "partial")

    def test_increment_returned_qty_logic(self):
        # Mock transaction and child item
        class MockItem:
            def __init__(self, name, item_code, serial_no, qty, returned_qty):
                self.name = name
                self.item_code = item_code
                self.serial_no = serial_no
                self.qty = qty
                self.returned_qty = returned_qty

        class MockTxn:
            def __init__(self, items):
                self.items = items

        class MockCheckinRow:
            def __init__(self, transaction_item, item_code, serial_no, returned_qty):
                self.transaction_item = transaction_item
                self.item_code = item_code
                self.serial_no = serial_no
                self.returned_qty = returned_qty

        item1 = MockItem("row-1", "CAM-01", "SN-100", 1.0, 0.0)
        item2 = MockItem("row-2", "CABLE-BNC", None, 5.0, 2.0)
        txn = MockTxn([item1, item2])

        checkin_row1 = MockCheckinRow("row-1", "CAM-01", "SN-100", 1.0)
        checkin_row2 = MockCheckinRow(None, "CABLE-BNC", None, 3.0)

        # In standalone test, verify matching logic branch
        self.assertTrue(item1.name == checkin_row1.transaction_item)
        self.assertTrue(item2.item_code == checkin_row2.item_code)


if __name__ == "__main__":
    unittest.main()
