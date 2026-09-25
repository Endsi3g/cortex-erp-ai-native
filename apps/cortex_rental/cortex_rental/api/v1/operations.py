"""Operations overview (the daily cockpit): every figure is a tenant-scoped query."""

from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role

ACTIVE_OUT_OF_SERVICE = ["Quarantine", "Under Repair", "Missing"]
RISK_WINDOW_HOURS = 48


def _rows(company: str, filters: Dict[str, Any], order_by: str) -> List[Dict[str, Any]]:
    rows = frappe.get_list(
        "Cortex Rental Transaction",
        filters={"company": company, **filters},
        fields=[
            "name",
            "customer",
            "project_name",
            "rental_state",
            "starts_at",
            "ends_at",
            "customer_account_ready",
            "insurance_ready",
            "payment_ready",
        ],
        order_by=order_by,
        limit_page_length=200,
    )
    customers = {row.customer for row in rows}
    names = (
        dict(
            frappe.get_all(
                "Customer", filters={"name": ["in", list(customers)]}, fields=["name", "customer_name"], as_list=True
            )
        )
        if customers
        else {}
    )
    return [
        {
            "name": row.name,
            "customer": row.customer,
            "customer_name": names.get(row.customer) or row.customer,
            "project_name": row.project_name or "",
            "rental_state": row.rental_state,
            "starts_at": str(row.starts_at),
            "ends_at": str(row.ends_at),
            "missing_requirements": [
                key
                for key in ("customer_account_ready", "insurance_ready", "payment_ready")
                if not int(row.get(key) or 0)
            ],
        }
        for row in rows
    ]


def overview_handler(company: str, day: str) -> Dict[str, Any]:
    start, end = f"{day} 00:00:00", f"{day} 23:59:59"
    now = frappe.utils.now_datetime()
    horizon = frappe.utils.add_to_date(now, hours=RISK_WINDOW_HOURS)

    departures = _rows(
        company,
        {"rental_state": ["in", ["Reservation", "Contract"]], "starts_at": ["between", [start, end]]},
        "starts_at asc",
    )
    returns = _rows(company, {"rental_state": "Checked Out", "ends_at": ["between", [start, end]]}, "ends_at asc")
    overdue = _rows(company, {"rental_state": "Checked Out", "ends_at": ["<", now]}, "ends_at asc")
    exceptions = _rows(company, {"rental_state": ["in", ["Quarantine", "Disputed"]]}, "modified desc")
    upcoming = _rows(
        company,
        {"rental_state": ["in", ["Reservation", "Contract"]], "starts_at": ["between", [now, horizon]]},
        "starts_at asc",
    )
    at_risk = [row for row in upcoming if row["missing_requirements"]]

    serials_out = frappe.get_list(
        "Serial No",
        filters={"company": company, "cortex_status": ["in", ACTIVE_OUT_OF_SERVICE]},
        fields=["name", "item_code", "cortex_status"],
        order_by="modified desc",
        limit_page_length=50,
    )
    approvals_pending = frappe.db.count("Approval Request", {"company": company, "status": "Pending"})
    inbound_pending = frappe.db.count(
        "Cortex Inbound Request", {"company": company, "status": ["in", ["Received", "Processing"]]}
    )

    return {
        "day": day,
        "generated_at": str(now),
        "kpis": {
            "departures": len(departures),
            "returns": len(returns),
            "overdue": len(overdue),
            "exceptions": len(exceptions) + len(serials_out),
            "approvals_pending": approvals_pending,
            "inbound_pending": inbound_pending,
        },
        "departures": departures,
        "returns": returns,
        "overdue": overdue,
        "exceptions": exceptions,
        "at_risk": at_risk,
        "serials_out_of_service": [
            {"serial_no": row.name, "item_code": row.item_code, "status": row.cortex_status} for row in serials_out
        ],
    }


if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_operations_overview(day: str = None):
        require_human_staff_role()
        company = get_company_context()
        day = str(frappe.utils.getdate(day)) if day else frappe.utils.today()
        return {"data": overview_handler(company, day), "meta": {"company": company}}
