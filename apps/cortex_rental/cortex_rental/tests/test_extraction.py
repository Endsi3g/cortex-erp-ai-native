import json
import unittest
from pathlib import Path

from cortex_rental.services.extraction import (
    CONFIDENCE_THRESHOLD,
    record_extraction_run,
    validate_extraction_payload,
)

VALID_PAYLOAD = {
    "customer": {"name": "Jane Doe", "confidence": 0.95},
    "rental_period": {
        "starts_at": "2026-09-01T09:00:00Z",
        "ends_at": "2026-09-08T09:00:00Z",
        "confidence": 0.9,
    },
    "items": [{"raw_text": "ARRI Alexa 35", "quantity": 1, "confidence": 0.9}],
    "metadata": {
        "source_channel": "email",
        "source_document_id": "doc-001",
        "language": "en",
        "overall_confidence": 0.92,
        "review_required": False,
        "evidence_ids": ["ev-1"],
    },
}


class TestExtractionSchemaValidation(unittest.TestCase):
    def test_valid_payload_passes(self):
        is_valid, errors = validate_extraction_payload(VALID_PAYLOAD)
        self.assertTrue(is_valid, errors)
        self.assertEqual(errors, [])

    def test_missing_required_top_level_field_is_rejected(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "items"}
        is_valid, errors = validate_extraction_payload(payload)
        self.assertFalse(is_valid)
        self.assertTrue(any("items" in e for e in errors))

    def test_missing_required_item_field_is_rejected(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        del payload["items"][0]["quantity"]
        is_valid, errors = validate_extraction_payload(payload)
        self.assertFalse(is_valid)

    def test_record_extraction_run_flags_low_confidence_for_review(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["metadata"]["overall_confidence"] = CONFIDENCE_THRESHOLD - 0.1
        result = record_extraction_run(
            company="CineRental Montreal", actor_id="agent:cortex-intake", extracted_payload=payload
        )
        self.assertTrue(result["review_required"])

    def test_record_extraction_run_does_not_flag_high_confidence_valid_payload(self):
        result = record_extraction_run(
            company="CineRental Montreal", actor_id="agent:cortex-intake", extracted_payload=VALID_PAYLOAD
        )
        self.assertEqual(result["validation_status"], "Valid")
        self.assertFalse(result["review_required"])

    def test_vendored_schema_matches_onyx_source_of_truth(self):
        """
        cortex_rental vendors its own copy of
        apps/cortex-onyx/schemas/intake_extraction_schema.json (see
        services/extraction.py docstring — a standalone Frappe app
        can't depend on a sibling monorepo path at runtime). This test
        only runs inside this monorepo's own CI and exists purely to
        catch drift between the two copies during development.
        """
        vendored = Path(__file__).resolve().parents[1] / "schemas" / "intake_extraction_schema.json"
        onyx_source = (
            Path(__file__).resolve().parents[4] / "apps" / "cortex-onyx" / "schemas" / "intake_extraction_schema.json"
        )
        if not onyx_source.exists():
            self.skipTest("cortex-onyx sibling directory not present (expected outside this monorepo)")

        self.assertEqual(
            json.loads(vendored.read_text()),
            json.loads(onyx_source.read_text()),
            "cortex_rental's vendored schema has drifted from apps/cortex-onyx/schemas/ — copy the source of "
            "truth back in.",
        )


if __name__ == "__main__":
    unittest.main()
