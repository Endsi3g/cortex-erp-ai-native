"""Grille de disponibilité : le parc réservable exclut les unités indisponibles et l'état réel est exposé."""

from types import SimpleNamespace
import unittest

from cortex_rental.api.v1 import availability


def _row(**kw):
    return SimpleNamespace(**kw)


class FakeDb:
    def __init__(self, serial_rows, out_rows=()):
        self.serial_rows = serial_rows
        self.out_rows = out_rows

    def table_exists(self, doctype):
        return True

    def has_column(self, doctype, column):
        return True

    def sql(self, query, params=None, as_dict=False):
        if "tabSerial No" in query:
            return self.serial_rows
        if "'Checked Out'" in query:
            return self.out_rows
        return []


class TestMatrixUnitStates(unittest.TestCase):
    def run_matrix(self, serial_rows, out_rows=()):
        profiles = [
            _row(item_code="CAM", item_name="Caméra", category="Camera", is_serialized=1, total_quantity=0),
            _row(item_code="CABLE", item_name="Câble", category="Grip", is_serialized=0, total_quantity=8),
        ]
        fake = SimpleNamespace(db=FakeDb(serial_rows, out_rows), get_all=lambda *a, **k: profiles)
        original = availability.frappe
        availability.frappe = fake
        try:
            return availability.get_matrix_handler(
                {"starts_at": "2026-10-10 00:00:00", "ends_at": "2026-10-17 00:00:00"}, "Cortex Test"
            )
        finally:
            availability.frappe = original

    def test_unavailable_units_leave_the_bookable_fleet_but_stay_visible(self):
        rows = [
            _row(item_code="CAM", unit_state="Active", count=3),
            _row(item_code="CAM", unit_state="Quarantine", count=1),
            _row(item_code="CAM", unit_state="Under Repair", count=1),
            _row(item_code="CAM", unit_state="Decommissioned", count=2),
        ]
        items = {i["item_code"]: i for i in self.run_matrix(rows, [_row(item_code="CAM", qty=2)])["items"]}
        camera = items["CAM"]
        self.assertEqual(camera["fleet_quantity"], 3)  # 7 unités au dossier, 3 réservables
        self.assertEqual(camera["unit_states"], {"Active": 3, "Quarantine": 1, "Under Repair": 1, "Decommissioned": 2})
        self.assertEqual(camera["out_now"], 2)

    def test_non_serialized_items_never_get_an_invented_state(self):
        items = {i["item_code"]: i for i in self.run_matrix([])["items"]}
        self.assertEqual(items["CABLE"]["fleet_quantity"], 8)
        self.assertIsNone(items["CABLE"]["unit_states"])
        self.assertEqual(items["CABLE"]["out_now"], 0)

    def test_serialized_item_without_units_reports_zero_fleet_and_unknown_states(self):
        items = {i["item_code"]: i for i in self.run_matrix([])["items"]}
        self.assertEqual(items["CAM"]["fleet_quantity"], 0)
        self.assertIsNone(items["CAM"]["unit_states"])


if __name__ == "__main__":
    unittest.main()
