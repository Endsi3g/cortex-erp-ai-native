from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_human_staff_role, get_company_context
from cortex_rental.services.checkin import (
    complete_checkin,
    process_checkin,
    search_active_transactions,
    lookup_scan_target,
)
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency

# NOTE: Human-staff-only endpoints (require_human_staff_role). Physical
# check-in and receiving require an authorized operator at the counter/warehouse.


def complete_checkin_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    checkin_name = payload.get("checkin_id")
    if not checkin_name:
        raise ValueError("checkin_id is required.")
    finalize_mode = payload.get("finalize_mode", "auto")
    return complete_checkin(checkin_name=checkin_name, actor_id=actor_id, finalize_mode=finalize_mode)


def submit_checkin_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    transaction_id = payload.get("transaction_id")
    if not transaction_id:
        raise ValueError("transaction_id is required.")

    items_raw = payload.get("items")
    if isinstance(items_raw, str):
        if frappe:
            items = frappe.parse_json(items_raw)
        else:
            import json
            items = json.loads(items_raw)
    else:
        items = items_raw or []

    if not items:
        raise ValueError("items array is required.")

    finalize_mode = payload.get("finalize_mode", "auto")
    notes = payload.get("notes", "")

    return process_checkin(
        company=company,
        actor_id=actor_id,
        transaction_id=transaction_id,
        items=items,
        finalize_mode=finalize_mode,
        notes=notes,
    )


if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_active_transactions(query: Optional[str] = None):
        require_human_staff_role()
        company = get_company_context()
        results = search_active_transactions(company=company, query=query)
        return {"data": results, "meta": {"company": company, "count": len(results)}}

    @frappe.whitelist(methods=["GET"])
    def lookup_scan(scan_code: str):
        require_human_staff_role()
        company = get_company_context()
        result = lookup_scan_target(company=company, scan_code=scan_code)
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    def submit_checkin():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="checkin.submit_checkin",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: submit_checkin_handler(payload=payload, company=company, actor_id=frappe.session.user),
        )
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    def complete_checkin_api():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="checkin.complete_checkin",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: complete_checkin_handler(payload=payload, company=company, actor_id=frappe.session.user),
        )
        return {"data": result, "meta": {"company": company}}
