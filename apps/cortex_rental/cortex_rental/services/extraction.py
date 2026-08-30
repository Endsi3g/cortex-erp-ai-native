"""
Structured extraction validation + provenance (PRD §2.1: "aucun agent
ne prend de décision métier à partir d'un texte libre... d'une donnée
extraite sans preuve"). This is the enforcement point that makes
apps/cortex-onyx/schemas/intake_extraction_schema.json more than
documentation: every extraction an agent claims to have made is
validated against it here before a Cortex Extraction Run record is
created, and low-confidence/invalid extractions are flagged for review
rather than silently accepted.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

try:
    import frappe
except ImportError:
    frappe = None

try:
    import jsonschema
except ImportError:
    jsonschema = None

CONFIDENCE_THRESHOLD = 0.85  # Matches SEUIL_CONFIANCE in cortex_intake_system.md — keep in sync.

# Vendored inside cortex_rental itself, NOT read from ../../cortex-onyx/.
# cortex_rental is a standalone Frappe app (installed via `bench get-app`
# from just this subtree) and cannot depend on a sibling monorepo
# directory being present at runtime. This is a deliberate copy of
# apps/cortex-onyx/schemas/intake_extraction_schema.json — kept in sync
# by tests/test_extraction.py, which fails the build if the two diverge.
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "intake_extraction_schema.json"
_schema_cache: Optional[Dict[str, Any]] = None


def _load_schema() -> Optional[Dict[str, Any]]:
    global _schema_cache
    if _schema_cache is None and _SCHEMA_PATH.exists():
        with open(_SCHEMA_PATH) as f:
            _schema_cache = json.load(f)
    return _schema_cache


def _minimal_validate(payload: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Fallback used only when the `jsonschema` package isn't installed:
    checks top-level required keys and each item's required keys.
    Not a full JSON Schema validator — real validation happens via
    `jsonschema` wherever it's available (it is a standard, well-known
    dependency; this fallback exists only so the pure-Python test suite
    in this sandbox doesn't hard-require it).
    """
    errors = []
    for key in schema.get("required", []):
        if key not in payload:
            errors.append(f"Missing required top-level field: {key}")

    items_schema = schema.get("properties", {}).get("items", {}).get("items", {})
    for req in items_schema.get("required", []):
        for i, item in enumerate(payload.get("items", [])):
            if req not in item:
                errors.append(f"items[{i}] missing required field: {req}")

    metadata_schema = schema.get("properties", {}).get("metadata", {})
    for req in metadata_schema.get("required", []):
        if req not in payload.get("metadata", {}):
            errors.append(f"metadata missing required field: {req}")

    return errors


def validate_extraction_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    schema = _load_schema()
    if not schema:
        return False, ["intake_extraction_schema.json not found — cannot validate."]

    if jsonschema:
        validator = jsonschema.Draft7Validator(schema)
        errors = [f"{'.'.join(str(p) for p in e.path)}: {e.message}" for e in validator.iter_errors(payload)]
    else:
        errors = _minimal_validate(payload, schema)

    return (len(errors) == 0, errors)


def record_extraction_run(
    company: str,
    actor_id: str,
    extracted_payload: Dict[str, Any],
    model_used: Optional[str] = None,
    inbound_request: Optional[str] = None,
    evidence_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Validate a claimed extraction against the schema and the confidence
    threshold, then record it — valid or not. An invalid or
    low-confidence extraction is recorded (with review_required=1), not
    rejected outright: it becomes visible for human review rather than
    silently discarded, matching the intake agent's own "Règle d'or #6".
    """
    is_valid, errors = validate_extraction_payload(extracted_payload)

    overall_confidence = float((extracted_payload.get("metadata") or {}).get("overall_confidence") or 0.0)
    review_required = (not is_valid) or overall_confidence < CONFIDENCE_THRESHOLD

    if not frappe:
        return {
            "id": "XTR-MOCK-001",
            "validation_status": "Valid" if is_valid else "Invalid",
            "validation_errors": errors,
            "review_required": review_required,
        }

    from cortex_rental.services.evidence import require_scanned_evidence

    if evidence_ids:
        require_scanned_evidence(company, evidence_ids)

    doc = frappe.get_doc(
        {
            "doctype": "Cortex Extraction Run",
            "company": company,
            "inbound_request": inbound_request,
            "evidence_references": frappe.as_json(evidence_ids or []),
            "extracted_payload": frappe.as_json(extracted_payload),
            "validation_status": "Valid" if is_valid else "Invalid",
            "validation_errors": frappe.as_json(errors),
            "overall_confidence": overall_confidence,
            "review_required": 1 if review_required else 0,
            "model_used": model_used,
            "actor_id": actor_id,
            "extracted_at": frappe.utils.now_datetime(),
        }
    )
    doc.flags.ignore_permissions = True
    doc.insert()

    return {
        "id": doc.name,
        "validation_status": doc.validation_status,
        "validation_errors": errors,
        "overall_confidence": overall_confidence,
        "review_required": review_required,
    }
