import unittest

from cortex_rental.services.checkin import DISPOSITION_TO_SERIAL_STATUS, complete_checkin


class TestCheckinDispositionMapping(unittest.TestCase):
    def test_every_disposition_maps_to_a_valid_cortex_status(self):
        """
        Regression guard: every disposition value in
        Cortex Check-In Item's `disposition` Select must map to one of
        the cortex_status values the Serial No Custom Field actually
        allows (fixtures/custom_field.json), or a check-in would try to
        set a Serial No to a status the field doesn't accept.
        """
        allowed_statuses = {"Active", "Quarantine", "Under Repair", "Missing", "Decommissioned"}
        for disposition, status in DISPOSITION_TO_SERIAL_STATUS.items():
            self.assertIn(status, allowed_statuses, f"{disposition} -> {status} is not an allowed cortex_status")

    def test_all_dispositions_from_the_doctype_select_are_mapped(self):
        doctype_dispositions = {"Return to Stock", "Quarantine", "Repair", "Missing", "Write-off"}
        self.assertEqual(set(DISPOSITION_TO_SERIAL_STATUS.keys()), doctype_dispositions)

    def test_complete_checkin_mock_mode_returns_stub(self):
        result = complete_checkin("CHK-2026-00001", actor_id="ops@cortex.local")
        self.assertEqual(result["status"], "Completed")


if __name__ == "__main__":
    unittest.main()
