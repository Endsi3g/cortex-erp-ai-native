"""Confirming or cancelling what the assistant proposed.

A proposal (Cortex AI Action) runs only when the person who owns the
conversation confirms it, at most once, within PROPOSAL_TTL_HOURS. The
write goes through the same endpoint the screens use, as that person:
role checks, state machine, idempotency and business audit all apply.
"""

from datetime import timedelta
from typing import Any, Callable, Dict, Tuple

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.ai.tools import _mod, call_endpoint

PROPOSAL_TTL_HOURS = 24


def _create_quote(a):
    result = call_endpoint(
        _mod("rentals").create_quote_draft,
        customer_id=a["customer_id"],
        starts_at=a["starts_at"],
        ends_at=a["ends_at"],
        items=[{"item_code": i["item_code"], "quantity": i["quantity"]} for i in a["items"]],
        project_name=a.get("project_name"),
        notes=a.get("notes"),
    )
    if result.get("status") != "completed" or not result.get("entity_id"):
        raise ValueError((result.get("errors") or [{}])[0].get("message") or "Soumission refusée.")
    return {"rental": result["entity_id"]}, f"/rentals/{result['entity_id']}"


def _confirm_reservation(a):
    result = call_endpoint(_mod("rentals").request_reservation, name=a["rental"])
    if result.get("status") != "completed":
        raise ValueError((result.get("errors") or [{}])[0].get("message") or "Réservation refusée.")
    return {"rental": a["rental"], "state": "Reservation"}, f"/rentals/{a['rental']}"


def _record_advance_payment(a):
    data = call_endpoint(
        _mod("billing").record_advance_payment,
        rental_id=a["rental"],
        amount=a["amount"],
        mode_of_payment=a["mode_of_payment"],
        reference_no=a.get("reference_no"),
    )
    return {"rental": a["rental"], **(data if isinstance(data, dict) else {})}, f"/rentals/{a['rental']}"


def _create_final_invoice(a):
    data = call_endpoint(_mod("billing").create_final_invoice, rental_id=a["rental"])
    return {"rental": a["rental"], **(data if isinstance(data, dict) else {})}, f"/rentals/{a['rental']}"


def _cancel_rental(a):
    call_endpoint(_mod("rentals").cancel_rental, name=a["rental"], reason=a["reason"])
    return {"rental": a["rental"], "state": "Cancelled"}, f"/rentals/{a['rental']}"


def _set_serial_status(a):
    call_endpoint(_mod("catalog").set_serial_status, serial_no=a["serial_no"], status=a["status"], reason=a["reason"])
    return {"serial_no": a["serial_no"], "status": a["status"]}, f"/serials/{a['serial_no']}"


def _create_customer(a):
    data = call_endpoint(
        _mod("clients").create_customer,
        customer_name=a["customer_name"],
        customer_type=a.get("customer_type") or "Company",
        email=a.get("email"),
        phone=a.get("phone"),
    )
    return {"customer": data["name"]}, f"/customers/{data['name']}"


def _reject_inbound(a):
    call_endpoint(_mod("ai").reject_inbound, source_id=a["source_id"], reason=a["reason"])
    return {"source_id": a["source_id"], "status": "Rejected"}, "/ai/inbox"


EXECUTORS: Dict[str, Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str]]] = {
    "create_quote": _create_quote,
    "confirm_reservation": _confirm_reservation,
    "record_advance_payment": _record_advance_payment,
    "create_final_invoice": _create_final_invoice,
    "cancel_rental": _cancel_rental,
    "set_serial_status": _set_serial_status,
    "create_customer": _create_customer,
    "reject_inbound_request": _reject_inbound,
}


class ActionRefused(Exception):
    """The decision itself is not allowed (not yours, already decided, expired…)."""


def check_decidable(action: Dict[str, Any], user: str, company: str, now) -> None:
    if action.get("company") != company:
        raise ActionRefused("Action introuvable pour la société active.")
    if action.get("user") != user:
        raise ActionRefused("Seule la personne qui a reçu cette proposition peut la décider.")
    if action.get("status") != "Proposed":
        raise ActionRefused(f"Cette action est déjà {str(action.get('status')).lower()}.")
    created = action.get("creation")
    if created and now - created > timedelta(hours=PROPOSAL_TTL_HOURS):
        raise ActionRefused("Cette proposition a expiré ; demandez à l’assistant de la refaire.")
    if action.get("tool") not in EXECUTORS:
        raise ActionRefused("Action inconnue.")


def execute(tool: str, arguments: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    return EXECUTORS[tool](arguments)
