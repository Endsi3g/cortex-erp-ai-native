"""Operations cockpit read model: today's workload, computed from real transactions.

Nothing here is estimated: every counter is a `count` over Cortex Rental Transaction,
Serial No, Approval Request or Cortex Inbound Request rows the caller may read.
"""

from datetime import timedelta
from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services import defense
from cortex_rental.api.v1._shared import envelope, now_iso
from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role

TRANSACTION = "Cortex Rental Transaction"
APPROVER_ROLES = {"System Manager", "Administrator", "Rental Manager", "Cortex Account Reviewer"}
TIMELINE_LIMIT = 50


def _day_bounds():
    start = frappe.utils.get_datetime(frappe.utils.today())
    return start, start + timedelta(days=1) - timedelta(seconds=1)


def overview_handler(company: str, can_decide_approvals: bool) -> Dict[str, Any]:
    day_start, day_end = _day_bounds()
    now = frappe.utils.now_datetime()
    base = {"company": company}
    departures_filter = {
        **base,
        "rental_state": ["in", ["Reservation", "Contract"]],
        "starts_at": ["between", [day_start, day_end]],
    }
    returns_filter = {**base, "rental_state": "Checked Out", "ends_at": ["between", [day_start, day_end]]}

    counts = {
        "departures_today": frappe.db.count(TRANSACTION, filters=departures_filter),
        "returns_due_today": frappe.db.count(TRANSACTION, filters=returns_filter),
        "overdue_returns": frappe.db.count(
            TRANSACTION, filters={**base, "rental_state": "Checked Out", "ends_at": ["<", now]}
        ),
        "disputed_or_quarantined": frappe.db.count(
            TRANSACTION, filters={**base, "rental_state": ["in", ["Disputed", "Quarantine"]]}
        ),
        "missing_serials": frappe.db.count("Serial No", filters={"company": company, "cortex_status": "Missing"}),
        "inbound_to_review": frappe.db.count("Cortex Inbound Request", filters={**base, "status": "Received"}),
        # Approval counts are only exposed to roles that can decide them.
        "pending_approvals": (
            frappe.db.count("Approval Request", filters={**base, "status": "Pending"}) if can_decide_approvals else None
        ),
    }
    counts["exceptions"] = counts["overdue_returns"] + counts["disputed_or_quarantined"] + counts["missing_serials"]

    timeline: List[Dict[str, Any]] = []
    for kind, flt, field in (("departure", departures_filter, "starts_at"), ("return", returns_filter, "ends_at")):
        rows = frappe.get_list(
            TRANSACTION,
            filters=flt,
            fields=["name", "customer", "rental_state", field],
            order_by=f"{field} asc",
            page_length=TIMELINE_LIMIT,
        )
        for row in rows:
            timeline.append(
                {
                    "kind": kind,
                    "rental_id": row.name,
                    "customer": row.customer,
                    "state": row.rental_state,
                    "at": str(row.get(field)),
                }
            )
    timeline.sort(key=lambda entry: entry["at"])
    return {"counts": counts, "timeline": timeline[:TIMELINE_LIMIT], "as_of": now_iso()}


if frappe:

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_operations_overview():
        require_human_staff_role()
        roles = set(frappe.get_roles(frappe.session.user))
        return envelope(overview_handler(get_company_context(), bool(roles & APPROVER_ROLES)))
