"""Read models behind the Cortex UI screens: catalogue, operations, AI inbox/audit, consignation.

Frappe is replaced by a mock, like the other unit tests; the live behaviour on a
bench is exercised separately (see docs/frontend/UI_REBUILD_PLAN.md, phase 5).
"""

import json
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from cortex_rental.api.v1 import catalog, consignment, intelligence, operations


class Row(dict):
    """dict with attribute access, like a frappe._dict row."""

    __getattr__ = dict.get


class Denied(Exception):
    pass


def fake_frappe(**overrides):
    mock = MagicMock()
    mock.throw.side_effect = Denied
    mock.PermissionError = Denied
    mock.DoesNotExistError = Denied
    mock.ValidationError = Denied
    mock.db.get_value.return_value = "CAD"
    mock.utils.now_datetime.return_value = MagicMock(isoformat=lambda: "2026-09-28T12:00:00")
    for key, value in overrides.items():
        setattr(mock, key, value)
    return mock


class TestCatalog(unittest.TestCase):
    def test_serialized_quantities_come_from_serial_statuses_and_open_rentals(self):
        profile = Row(
            item_code="CAM-1",
            item_name="Camera",
            category="Camera Bodies",
            daily_rate=1500,
            is_serialized=1,
            total_quantity=0,
            required_accessories="Batterie, Chargeur\nCarte",
        )
        counts = {"Active": 5, "Under Repair": 1, "Quarantine": 1, "Missing": 1}
        item = catalog.serialize_equipment(profile, counts, rented=2.0, currency="CAD")
        self.assertEqual(item["total_fleet_quantity"], 8)
        self.assertEqual(item["maintenance_quantity"], 2)
        self.assertEqual(item["rented_quantity"], 2)
        self.assertEqual(item["available_quantity"], 3)  # 8 - 2 rented - 2 maintenance - 1 missing
        self.assertEqual(item["required_accessories"], ["Batterie", "Chargeur", "Carte"])

    def test_values_the_erp_does_not_hold_are_omitted_not_invented(self):
        item = catalog.serialize_equipment(Row(item_code="X", is_serialized=0, total_quantity=4), {}, 0.0, "CAD")
        for missing in ("brand", "weekly_rate", "monthly_rate", "image_url"):
            self.assertNotIn(missing, item)
        self.assertEqual(item["available_quantity"], 4)

    def test_available_quantity_never_negative(self):
        item = catalog.serialize_equipment(
            Row(item_code="X", is_serialized=0, total_quantity=1), {}, rented=3.0, currency="CAD"
        )
        self.assertEqual(item["available_quantity"], 0)

    def test_list_equipment_is_company_scoped(self):
        mock = fake_frappe()
        mock.db.count.return_value = 1
        mock.get_list.return_value = [
            Row(
                item_code="CAM-1",
                item_name="Camera",
                category="Camera Bodies",
                daily_rate=10,
                is_serialized=0,
                total_quantity=2,
                required_accessories="",
            )
        ]
        mock.get_all.return_value = []
        with patch.object(catalog, "frappe", mock):
            result = catalog.list_equipment_handler("ACME", "Lighting", "cam", 1, 20)
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(mock.get_list.call_args.kwargs["filters"], {"company": "ACME", "category": "Lighting"})
        self.assertEqual(mock.get_list.call_args.kwargs["or_filters"][0][:2], ["item_code", "like"])

    def test_serial_of_another_company_is_hidden(self):
        mock = fake_frappe()
        mock.has_permission.return_value = True
        mock.get_doc.return_value = Row(name="SN-1", company="OTHER")
        with patch.object(catalog, "frappe", mock), self.assertRaises(Denied):
            catalog.get_serial_handler("ACME", "SN-1")

    def test_serial_out_on_a_rental_is_checked_out(self):
        mock = fake_frappe()
        mock.has_permission.return_value = True
        mock.get_doc.return_value = Row(
            name="SN-1", company="ACME", item_code="CAM-1", item_name="Camera", cortex_status="Active", warehouse="Main"
        )
        mock.get_all.side_effect = [[Row(parent="CR-1")], ["Checked Out"], []]
        with patch.object(catalog, "frappe", mock):
            serial = catalog.get_serial_handler("ACME", "SN-1")
        self.assertEqual(serial["status"], "Checked Out")
        self.assertFalse(serial["is_consigned"])
        self.assertNotIn("owner_id", serial)


class TestOperations(unittest.TestCase):
    def test_counts_are_scoped_and_approvals_hidden_from_non_approvers(self):
        mock = fake_frappe()
        mock.utils.get_datetime.return_value = date(2026, 9, 28)
        mock.utils.today.return_value = "2026-09-28"
        mock.db.count.return_value = 2
        mock.get_list.return_value = []
        with patch.object(operations, "frappe", mock):
            data = operations.overview_handler("ACME", can_decide_approvals=False)
        self.assertIsNone(data["counts"]["pending_approvals"])
        self.assertEqual(data["counts"]["exceptions"], 6)  # overdue + disputed + missing serials
        for call in mock.db.count.call_args_list:
            self.assertEqual(call.kwargs["filters"]["company"], "ACME")


class TestIntelligence(unittest.TestCase):
    PAYLOAD = {
        "customer": {"name": "Acme"},
        "rental_period": {"starts_at": "2026-10-01T09:00:00Z"},
        "items": [{"raw_text": "Alexa 35", "matched_item_id": "CAM-1", "quantity": 1, "confidence": 0.9}],
    }

    def test_missing_fields_are_computed_from_the_payload(self):
        self.assertEqual(intelligence._missing_fields(self.PAYLOAD), ["Période de location"])
        self.assertEqual(intelligence._missing_fields({}), ["Client", "Période de location", "Équipement"])

    def test_inbound_without_recorded_confidence_is_null(self):
        row = Row(
            name="INB-1",
            source_channel="PDF Upload",
            sender_email="a@b.c",
            subject="Demande",
            raw_payload="x" * 30000,
            status="Received",
            creation="2026-09-28 10:00:00",
        )
        item = intelligence.serialize_inbound(row, None)
        self.assertIsNone(item["overall_confidence"])
        self.assertEqual(item["source"], "pdf")
        self.assertEqual(item["status"], "new")
        self.assertEqual(len(item["raw_body"]), 20000)

    def test_inbound_status_mapping(self):
        self.assertEqual(
            intelligence._inbound_status(Row(status="Processed", extracted_transaction="CR-1")), "converted"
        )
        self.assertEqual(intelligence._inbound_status(Row(status="Processed")), "reviewed")
        self.assertEqual(intelligence._inbound_status(Row(status="Rejected")), "dismissed")

    def test_draft_state_and_confidence(self):
        run = Row(
            name="XTR-1",
            inbound_request="INB-1",
            overall_confidence=0.62,
            review_required=1,
            validation_status="Valid",
            extracted_payload=json.dumps(self.PAYLOAD),
            extracted_at="2026-09-28 10:05:00",
        )
        draft = intelligence.serialize_draft(run, Row(subject="Demande", status="Received"))
        self.assertEqual(draft["ai_state"], "needs_confirmation")
        self.assertEqual(draft["status"], "pending_review")
        self.assertEqual(draft["confidence_score"], 0.62)
        self.assertEqual(draft["proposed_payload"]["customer_name"], "Acme")

    def test_bad_json_never_raises(self):
        run = Row(
            name="XTR-2",
            inbound_request=None,
            overall_confidence=None,
            review_required=0,
            validation_status="Valid",
            extracted_payload="{not json",
            extracted_at=None,
        )
        draft = intelligence.serialize_draft(run, None)
        self.assertIsNone(draft["confidence_score"])
        self.assertEqual(draft["ai_state"], "proposed")

    def test_audit_filters_are_company_scoped(self):
        mock = fake_frappe()
        mock.db.count.return_value = 0
        mock.get_list.return_value = []
        with patch.object(intelligence, "frappe", mock):
            intelligence.audit_handler("ACME", "Cortex Rental Transaction", None, None, 1, 20)
        self.assertEqual(
            mock.get_list.call_args.kwargs["filters"], {"company": "ACME", "entity_type": "Cortex Rental Transaction"}
        )


class TestConsignation(unittest.TestCase):
    def test_month_bounds(self):
        with patch.object(consignment, "frappe", fake_frappe()):
            self.assertEqual(consignment.month_bounds("2026-02"), (date(2026, 2, 1), date(2026, 2, 28)))
            with self.assertRaises(Denied):
                consignment.month_bounds("2026-13")
            with self.assertRaises(Denied):
                consignment.month_bounds("septembre")

    def test_statement_only_exposes_owner_safe_fields(self):
        mock = fake_frappe()
        mock.get_list.side_effect = [
            [Row(name="OWN-A", owner_name="Alex", short_code="A")],
            [
                Row(
                    name="PAYOUT-1",
                    owner="OWN-A",
                    serial_no="SN-1",
                    status="Calculated",
                    net_amount=900,
                    discount_amount=100,
                    consignment_percentage=70,
                    owner_payout_amount=630,
                    calculation_snapshot=json.dumps({"days": 3, "rate": 300, "renter": "SECRET"}),
                )
            ],
        ]
        mock.get_all.return_value = [Row(name="SN-1", item_code="CAM-1", item_name="Camera")]
        mock.utils.get_system_timezone.return_value = "America/Toronto"
        with patch.object(consignment, "frappe", mock):
            result = consignment.statement_handler("ACME", "OWN-A", "2026-09")["statement"]
        self.assertEqual(result["totals"], {"eligible_net_revenue": 900.0, "owner_amount_due": 630.0})
        self.assertEqual(
            set(result["lines"][0]),
            {
                "serial_number",
                "equipment_name",
                "billable_days",
                "rate",
                "discount_amount",
                "consignment_percentage",
                "owner_amount",
            },
        )
        self.assertNotIn("SECRET", json.dumps(result))

    def test_unknown_owner_is_refused(self):
        mock = fake_frappe()
        mock.get_list.return_value = []
        with patch.object(consignment, "frappe", mock), self.assertRaises(Denied):
            consignment.statement_handler("ACME", "OWN-X", "2026-09")


if __name__ == "__main__":
    unittest.main()
