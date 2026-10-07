"""Retour par numéro de série : chaque unité s'additionne sur la ligne (régression : la ligne restait à 1 sur 2)."""

import os
import unittest

BASE = os.path.dirname(os.path.dirname(__file__))


def source():
    with open(os.path.join(BASE, "services", "checkin.py"), encoding="utf-8") as handle:
        return handle.read()


class TestSerialReturnsAddUp(unittest.TestCase):
    def body(self):
        return source().split("def _increment_returned_qty")[1].split("\ndef ")[0]

    def test_the_running_total_is_read_from_the_database_not_the_stale_copy(self):
        body = self.body()
        self.assertIn('frappe.db.get_value("Cortex Rental Transaction Item", item.name, "returned_qty")', body)
        self.assertNotIn("current_qty = float(item.returned_qty", body)

    def test_the_in_memory_line_is_kept_in_step(self):
        self.assertIn("item.returned_qty = current_qty + added_qty", self.body())


if __name__ == "__main__":
    unittest.main()
