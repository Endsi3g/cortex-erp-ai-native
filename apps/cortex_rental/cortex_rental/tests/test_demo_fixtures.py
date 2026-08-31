# Copyright (c) 2026, Cortex Rental and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import MagicMock, patch
from cortex_rental.fixtures import demo_data


class TestDemoFixtures(unittest.TestCase):
    def test_provision_demo_data_without_frappe(self):
        with patch.object(demo_data, "frappe", None):
            res = demo_data.provision_demo_data()
            self.assertEqual(res["status"], "skipped")

    def test_provision_demo_data_with_mock_frappe(self):
        mock_frappe = MagicMock()
        mock_frappe.db.exists.return_value = False
        mock_frappe.get_all.return_value = []
        mock_frappe.db.get_value.return_value = None

        mock_doc = MagicMock()
        mock_doc.name = "MOCK-DOC-1"
        mock_frappe.get_doc.return_value = mock_doc

        with patch.object(demo_data, "frappe", mock_frappe):
            res = demo_data.provision_demo_data()
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["company"], "Cortex Cinema Rentals")
            self.assertGreater(res["items_count"], 0)
            mock_frappe.db.commit.assert_called()


if __name__ == "__main__":
    unittest.main()
