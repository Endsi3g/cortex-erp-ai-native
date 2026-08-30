"""
Idempotency-Key enforcement for Cortex Rental mutating endpoints (PRD §6
requirement: every write endpoint must support an Idempotency-Key).

A retried call with the same (Company, scope, Idempotency-Key) tuple
replays the original recorded response instead of creating a duplicate
document (duplicate quote, duplicate approval request, duplicate
consignment payout, duplicate customer). Reusing a key with a different
payload is rejected rather than silently returning a mismatched response.
"""
from typing import Any, Callable, Dict, Optional
import hashlib
import json

try:
    import frappe
except ImportError:
    frappe = None


def get_idempotency_key_header() -> Optional[str]:
    """Read the Idempotency-Key header from the current request, if any."""
    if not frappe:
        return None
    request = getattr(frappe.local, "request", None)
    key = request.headers.get("Idempotency-Key") if request else None
    return key or None


def _record_name(company: str, scope: str, idempotency_key: str) -> str:
    raw = f"{company}::{scope}::{idempotency_key}"
    return "IDEMP-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _hash_payload(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def with_idempotency(
    company: str,
    scope: str,
    idempotency_key: Optional[str],
    payload: Dict[str, Any],
    handler: Callable[[], Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Execute `handler()` at most once per (company, scope, idempotency_key).
    Callers that omit the key still get the mutation executed, but without
    dedup — supplying a key is how a retry-safe caller (agents in
    particular) opts in to safety.
    """
    if not frappe or not idempotency_key:
        return handler()

    name = _record_name(company, scope, idempotency_key)
    payload_hash = _hash_payload(payload)

    existing = frappe.db.get_value(
        "Cortex Idempotency Record", name, ["response_snapshot", "payload_hash"], as_dict=True
    )
    if existing:
        if existing.payload_hash != payload_hash:
            frappe.throw(
                "Idempotency-Key reuse with a different request payload is not allowed.",
                frappe.ValidationError,
            )
        return json.loads(existing.response_snapshot)

    result = handler()

    record = frappe.get_doc(
        {
            "doctype": "Cortex Idempotency Record",
            "name": name,
            "company": company,
            "scope": scope,
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
            "response_snapshot": frappe.as_json(result),
        }
    )
    record.flags.ignore_permissions = True
    try:
        record.insert()
    except frappe.DuplicateEntryError:
        # A concurrent retry raced us to the same key; return the winner's
        # recorded response rather than the (possibly duplicate) result of
        # this execution.
        winner = frappe.db.get_value("Cortex Idempotency Record", name, "response_snapshot")
        return json.loads(winner) if winner else result

    return result
