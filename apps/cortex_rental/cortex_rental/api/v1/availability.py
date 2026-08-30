from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import (
    require_agent_scope,
    require_human_staff_role,
    get_company_context,
)
from cortex_rental.services.availability import AvailabilityService
from cortex_rental.services.audit import AuditService
from cortex_rental.services.agent_telemetry import log_tool_call

# Blocking states count against fleet capacity; Quote never blocks (PRD:
# a quote is a non-binding draft) — matches the state list already used
# by AvailabilityService.check()'s overlap query.
BLOCKING_MATRIX_STATES = ("Reservation", "Contract", "Checked Out")
ALL_MATRIX_STATES = ("Quote",) + BLOCKING_MATRIX_STATES


def check_availability_handler(payload: Dict[str, Any], company: str) -> List[Dict[str, Any]]:
    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    item_requests = payload.get("items") or payload.get("item_requests") or []

    svc = AvailabilityService()
    results = svc.check(company=company, starts_at=starts_at, ends_at=ends_at, item_requests=item_requests)
    return results


if frappe:

    @frappe.whitelist(methods=["POST"])
    @log_tool_call("check_inventory_availability", scope="agent:availability:read")
    def check_availability():
        require_agent_scope("agent:availability:read")
        company = get_company_context()
        payload = frappe.local.form_dict
        results = check_availability_handler(payload=payload, company=company)
        AuditService.record_read(
            action="cortex.availability.checked", metadata={"item_count": len(results)}, company=company
        )
        return {"data": results, "meta": {"company": company}}


def get_matrix_handler(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    """
    Human-facing grid read for the Cortex Availability desk page: items x
    transactions overlapping a date window, for rendering a calendar-style
    matrix. Distinct from `check_availability_handler` above (which
    answers "can I book N units of item X" for the agent/quote flow) —
    this instead lists every overlapping transaction per item so the UI
    can draw a block per reservation/contract, not just a yes/no count.
    """
    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    if not starts_at or not ends_at:
        raise ValueError("starts_at and ends_at are required.")

    search = (payload.get("search") or "").strip().lower()
    category = payload.get("category") or None

    item_filters: Dict[str, Any] = {"company": company}
    if category:
        item_filters["category"] = category

    if not frappe:
        return {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "items": [],
            "notes": "Mocked result — no live Frappe/DB connection in this environment.",
        }

    profiles = frappe.get_all(
        "Cortex Rental Item Profile",
        filters=item_filters,
        fields=["item_code", "item_name", "category", "is_serialized", "total_quantity"],
        order_by="item_name asc",
        limit_page_length=200,
    )
    if search:
        profiles = [
            p
            for p in profiles
            if search in (p.item_name or "").lower() or search in (p.item_code or "").lower()
        ]

    item_codes = [p.item_code for p in profiles]

    fleet_by_item: Dict[str, float] = {}
    for p in profiles:
        if p.is_serialized:
            fleet_by_item[p.item_code] = frappe.db.count(
                "Serial No", {"company": company, "item_code": p.item_code}
            )
        else:
            fleet_by_item[p.item_code] = float(p.total_quantity or 0)

    blocks_by_item: Dict[str, List[Dict[str, Any]]] = {code: [] for code in item_codes}
    if item_codes:
        rows = frappe.db.sql(
            """
            SELECT t.name AS transaction, t.rental_state, t.customer,
                   t.starts_at, t.ends_at, ti.item_code, ti.qty
            FROM `tabCortex Rental Transaction Item` ti
            JOIN `tabCortex Rental Transaction` t ON t.name = ti.parent
            WHERE t.company = %(company)s
              AND ti.item_code IN %(item_codes)s
              AND t.rental_state IN %(states)s
              AND t.starts_at < %(ends_at)s
              AND t.ends_at > %(starts_at)s
            ORDER BY t.starts_at ASC
            """,
            {
                "company": company,
                "item_codes": item_codes,
                "states": ALL_MATRIX_STATES,
                "starts_at": starts_at,
                "ends_at": ends_at,
            },
            as_dict=True,
        )
        for row in rows:
            blocks_by_item.setdefault(row.item_code, []).append(
                {
                    "transaction": row.transaction,
                    "rental_state": row.rental_state,
                    "customer": row.customer,
                    "starts_at": str(row.starts_at),
                    "ends_at": str(row.ends_at),
                    "qty": float(row.qty),
                }
            )

    items_response = []
    for p in profiles:
        code = p.item_code
        item_blocks = blocks_by_item.get(code, [])
        # NOTE: this is a coarse conflict signal — it sums blocking qty
        # across the *entire* requested window rather than sweeping
        # day-by-day, so it can under-report a conflict that only exists
        # on a sub-range of the window (e.g. two 3-day bookings inside a
        # 7-day view that never actually overlap each other). Real
        # booking safety is enforced server-side by AvailabilityService
        # at transaction-confirmation time regardless of what this grid
        # shows — this is a visual aid, not the authority.
        blocking_qty = sum(b["qty"] for b in item_blocks if b["rental_state"] in BLOCKING_MATRIX_STATES)
        items_response.append(
            {
                "item_code": code,
                "item_name": p.item_name,
                "category": p.category,
                "is_serialized": bool(p.is_serialized),
                "fleet_quantity": fleet_by_item.get(code, 0),
                "blocks": item_blocks,
                "has_conflict": blocking_qty > fleet_by_item.get(code, 0),
            }
        )

    return {"starts_at": starts_at, "ends_at": ends_at, "items": items_response}


if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_matrix():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        result = get_matrix_handler(payload=payload, company=company)
        return {"data": result, "meta": {"company": company}}
