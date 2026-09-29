import calendar
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.api.v1._shared import envelope, page_args, parse_json, to_float
from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context, require_human_staff_role
from cortex_rental.services.consignment import ConsignmentService
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency
from cortex_rental.services.agent_telemetry import log_tool_call


def prepare_owner_statement_handler(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    owner_id = payload.get("owner_id")
    gross_amount = float(payload.get("gross_amount") or 0.0)
    consignment_percentage = float(payload.get("consignment_percentage") or 70.0)
    serial_no = payload.get("serial_no") or "SN-GENERIC-001"
    days = float(payload.get("days") or 3.0)
    rate = float(payload.get("rate") or 1500.0)

    payout_data = ConsignmentService.calculate_payout(
        gross_amount=gross_amount,
        consignment_percentage=consignment_percentage,
        serial_no=serial_no,
        days=days,
        rate=rate,
        metadata={"note": "Automated statement prepared via FastMCP"},
    )

    doc_id = "PAYOUT-DRAFT-001"

    if frappe:
        doc = frappe.get_doc(
            {
                "doctype": "Consignment Payout",
                "company": company,
                "owner": owner_id,
                "gross_amount": gross_amount,
                "consignment_percentage": consignment_percentage,
                "owner_payout_amount": payout_data["owner_payout_amount"],
                "calculation_snapshot": frappe.as_json(payout_data["calculation_snapshot"]),
            }
        )
        doc.insert(ignore_permissions=True)
        doc_id = doc.name

    AuditService.record_mutation(
        company=company,
        action="cortex.consignment.statement_prepared",
        entity_type="Consignment Payout",
        entity_id=doc_id,
        after_state={"owner": owner_id, "payout_amount": payout_data["owner_payout_amount"]},
    )

    return {
        "id": doc_id,
        "owner_id": owner_id,
        "gross_amount": gross_amount,
        "consignment_percentage": consignment_percentage,
        "owner_payout_amount": payout_data["owner_payout_amount"],
        "calculation_snapshot": payout_data["calculation_snapshot"],
    }


PAYOUT = "Consignment Payout"
OPEN_PAYOUT = ["Calculated", "Approved"]
STATEMENT_STATUS = {"Calculated": "draft", "Approved": "approved", "Paid": "paid"}


def month_bounds(period: Optional[str]) -> Tuple[date, date]:
    """`YYYY-MM` -> first and last day of that month (current month when omitted)."""
    today = date.today()
    try:
        year, month = (int(part) for part in (period or f"{today.year}-{today.month:02d}").split("-"))
        first = date(year, month, 1)
    except (ValueError, TypeError):
        frappe.throw("Période invalide: utiliser AAAA-MM.", frappe.ValidationError)
    return first, date(year, month, calendar.monthrange(year, month)[1])


def _payouts(company: str, start: date, end: date, owner: Optional[str] = None) -> List[Any]:
    filters: Dict[str, Any] = {
        "company": company,
        "status": ["!=", "Cancelled"],
        "creation": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]],
    }
    if owner:
        filters["owner"] = owner
    return frappe.get_list(
        PAYOUT,
        filters=filters,
        fields=[
            "name",
            "owner",
            "serial_no",
            "status",
            "net_amount",
            "discount_amount",
            "consignment_percentage",
            "owner_payout_amount",
            "calculation_snapshot",
        ],
        limit_page_length=0,
    )


def _serial_items(serials: List[str]) -> Dict[str, Dict[str, str]]:
    if not serials:
        return {}
    rows = frappe.get_all(
        "Serial No", filters={"name": ["in", serials]}, fields=["name", "item_code", "item_name"], limit_page_length=0
    )
    return {row.name: {"item_code": row.item_code, "item_name": row.item_name or row.item_code} for row in rows}


def list_owners_handler(company: str, search: Optional[str], page: int, page_size: int) -> Dict[str, Any]:
    filters: Dict[str, Any] = {"company": company}
    or_filters = None
    if search and search.strip():
        token = f"%{search.strip()}%"
        or_filters = [["owner_name", "like", token], ["short_code", "like", token]]
    total = frappe.db.count("Consignment Owner", filters=filters)
    owners = frappe.get_list(
        "Consignment Owner",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "owner_name", "short_code", "email", "phone", "default_percentage"],
        order_by="owner_name asc",
        start=(page - 1) * page_size,
        page_length=page_size,
    )
    payouts = (
        frappe.get_all(
            PAYOUT,
            filters={"company": company, "owner": ["in", [o.name for o in owners]], "status": ["!=", "Cancelled"]},
            fields=["owner", "serial_no", "status", "owner_payout_amount"],
            limit_page_length=0,
        )
        if owners
        else []
    )
    items = []
    for owner in owners:
        mine = [p for p in payouts if p.owner == owner.name]
        items.append(
            {
                "id": owner.name,
                "owner_code": owner.short_code or owner.name,
                "display_name": owner.owner_name,
                "contact_email": owner.email or "",
                **({"contact_phone": owner.phone} if owner.phone else {}),
                "default_commission_percentage": to_float(owner.default_percentage),
                "active_serials_count": len({p.serial_no for p in mine if p.serial_no}),
                "pending_payout_amount": round(
                    sum(to_float(p.owner_payout_amount) for p in mine if p.status in OPEN_PAYOUT), 2
                ),
                "currency": frappe.db.get_value("Company", company, "default_currency") or "CAD",
            }
        )
    return {"items": items, "total_count": total}


def dashboard_handler(company: str, period: Optional[str]) -> Dict[str, Any]:
    start, end = month_bounds(period)
    prev_year, prev_month = (start.year - 1, 12) if start.month == 1 else (start.year, start.month - 1)
    prev_start, prev_last = (
        date(prev_year, prev_month, 1),
        date(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1]),
    )
    current, previous = _payouts(company, start, end), _payouts(company, prev_start, prev_last)
    items = _serial_items([p.serial_no for p in current if p.serial_no])
    top: Dict[str, Dict[str, Any]] = {}
    for payout in current:
        info = items.get(payout.serial_no, {"item_code": payout.serial_no or "", "item_name": payout.serial_no or ""})
        entry = top.setdefault(
            info["item_code"],
            {
                "item_code": info["item_code"],
                "item_name": info["item_name"],
                "owner_code": payout.owner,
                "revenue_generated": 0.0,
                "owner_payout": 0.0,
            },
        )
        entry["revenue_generated"] += to_float(payout.net_amount)
        entry["owner_payout"] += to_float(payout.owner_payout_amount)
    owners = {
        o.name: o.owner_name
        for o in frappe.get_all(
            "Consignment Owner", filters={"company": company}, fields=["name", "owner_name"], limit_page_length=0
        )
    }
    pending: Dict[str, Dict[str, Any]] = {}
    for payout in current:
        if payout.status == "Paid":
            continue
        row = pending.setdefault(
            payout.owner,
            {
                "owner_id": payout.owner,
                "owner_name": owners.get(payout.owner, payout.owner),
                "period": f"{start.year}-{start.month:02d}",
                "amount_due": 0.0,
                "status": STATEMENT_STATUS.get(payout.status, "draft"),
            },
        )
        row["amount_due"] = round(row["amount_due"] + to_float(payout.owner_payout_amount), 2)
    return {
        "current_month_total_payout": round(sum(to_float(p.owner_payout_amount) for p in current), 2),
        "previous_month_total_payout": round(sum(to_float(p.owner_payout_amount) for p in previous), 2),
        "active_owners_count": len(owners),
        "active_consigned_serials_count": len({p.serial_no for p in current if p.serial_no}),
        "top_earning_items": sorted(top.values(), key=lambda e: e["owner_payout"], reverse=True)[:5],
        "pending_statements": list(pending.values()),
    }


def statement_handler(company: str, owner_id: str, period: str) -> Dict[str, Any]:
    """Owner statement restricted to what an owner may see: no renter, contact or project data."""
    owner = frappe.get_list(
        "Consignment Owner",
        filters={"company": company, "name": owner_id},
        fields=["name", "owner_name", "short_code"],
        page_length=1,
    )
    if not owner:
        frappe.throw("Propriétaire introuvable.", frappe.DoesNotExistError)
    start, end = month_bounds(period)
    payouts = _payouts(company, start, end, owner_id)
    items = _serial_items([p.serial_no for p in payouts if p.serial_no])
    lines = []
    for payout in payouts:
        snapshot = parse_json(payout.calculation_snapshot, {})
        lines.append(
            {
                "serial_number": payout.serial_no or "",
                "equipment_name": items.get(payout.serial_no, {}).get("item_name", payout.serial_no or ""),
                "billable_days": to_float(snapshot.get("days")),
                "rate": to_float(snapshot.get("rate")),
                "discount_amount": to_float(payout.discount_amount),
                "consignment_percentage": to_float(payout.consignment_percentage),
                "owner_amount": to_float(payout.owner_payout_amount),
            }
        )
    return {
        "statement": {
            "owner": {
                "id": owner[0].name,
                "display_name": owner[0].owner_name,
                "code": owner[0].short_code or owner[0].name,
            },
            "period": {"start": str(start), "end": str(end), "timezone": frappe.utils.get_system_timezone()},
            "currency": frappe.db.get_value("Company", company, "default_currency") or "CAD",
            "totals": {
                "eligible_net_revenue": round(sum(to_float(p.net_amount) for p in payouts), 2),
                "owner_amount_due": round(
                    sum(to_float(p.owner_payout_amount) for p in payouts if p.status != "Paid"), 2
                ),
            },
            "lines": lines,
            "generated_at": frappe.utils.now_datetime().isoformat(),
            "snapshot_version": f"{owner_id}:{start.year}-{start.month:02d}:{len(payouts)}",
        }
    }


def _require_payout_access() -> None:
    if not frappe.has_permission(PAYOUT, "read"):
        frappe.throw("Accès refusé aux versements de consignation.", frappe.PermissionError)


if frappe:

    @frappe.whitelist(methods=["POST"])
    @log_tool_call("prepare_owner_statement", scope="agent:consignment:read")
    def prepare_owner_statement():
        require_agent_scope("agent:consignment:read")
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="consignment.prepare_owner_statement",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: prepare_owner_statement_handler(payload=payload, company=company),
        )
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["GET"])
    def list_owners(search: str = None, page: int = 1, page_size: int = 20):
        require_human_staff_role()
        if not frappe.has_permission("Consignment Owner", "read"):
            frappe.throw("Accès refusé aux propriétaires en consignation.", frappe.PermissionError)
        page, page_size = page_args(page, page_size)
        return envelope(list_owners_handler(get_company_context(), search, page, page_size))

    @frappe.whitelist(methods=["GET"])
    def get_consignment_dashboard(period: str = None):
        require_human_staff_role()
        _require_payout_access()
        return envelope(dashboard_handler(get_company_context(), period))

    @frappe.whitelist(methods=["GET"])
    def get_owner_statement(owner_id: str, period: str):
        require_human_staff_role()
        _require_payout_access()
        return envelope(statement_handler(get_company_context(), owner_id, period))
