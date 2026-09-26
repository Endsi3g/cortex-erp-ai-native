"""
Consignment calculation and statement service.
Computes owner revenue share while strictly enforcing tenant/renter identity redaction.
"""

from typing import Any, Dict, Optional

try:
    import frappe
except ImportError:
    frappe = None


class ConsignmentService:
    # Single source of truth for renter/customer PII keys forbidden from
    # an owner-facing consignment payout snapshot or statement. Also
    # imported verbatim by ConsignmentPayout.validate() so the API-layer
    # sanitization and the DocType-level backstop can never drift apart
    # again (they previously used two different, non-overlapping lists).
    FORBIDDEN_RENTER_KEYS = [
        "customer",
        "customer_name",
        "customer_email",
        "customer_phone",
        "client_name",
        "client_email",
        "client_company",
        "renter_name",
        "renter_email",
        "renter_company",
        "billing_address",
        "contact_phone",
        "contact_name",
    ]

    # Only these top-level fields are ever written into a payout
    # snapshot — an allowlist, not just a denylist, so a future field
    # added to the raw calculation input isn't included by default.
    ALLOWED_SNAPSHOT_KEYS = frozenset(
        {"serial_no", "days", "rate", "gross_amount", "consignment_percentage", "payout_amount", "metadata"}
    )

    @classmethod
    def sanitize_snapshot(cls, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize payout snapshot: keep only allowlisted top-level keys,
        then recursively strip any forbidden renter/customer identity key
        at any nesting level (defense in depth for free-form fields like
        `metadata`, which callers may populate with arbitrary content).
        """
        sanitized = {}
        for key, value in snapshot_data.items():
            if key not in cls.ALLOWED_SNAPSHOT_KEYS:
                continue
            sanitized[key] = cls._strip_forbidden_keys(value)
        return sanitized

    @classmethod
    def _strip_forbidden_keys(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: cls._strip_forbidden_keys(v) for k, v in value.items() if k.lower() not in cls.FORBIDDEN_RENTER_KEYS
            }
        if isinstance(value, list):
            return [cls._strip_forbidden_keys(v) for v in value]
        return value

    @classmethod
    def calculate_payout(
        cls,
        gross_amount: float,
        consignment_percentage: float,
        serial_no: str,
        days: float,
        rate: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate owner payout amount and create sanitized calculation snapshot.
        """
        pct = float(consignment_percentage if consignment_percentage is not None else 70.0)
        payout_amount = round(gross_amount * (pct / 100.0), 2)

        raw_snapshot = {
            "serial_no": serial_no,
            "days": days,
            "rate": rate,
            "gross_amount": gross_amount,
            "consignment_percentage": pct,
            "payout_amount": payout_amount,
            "metadata": metadata or {},
        }

        sanitized_snapshot = cls.sanitize_snapshot(raw_snapshot)

        return {
            "gross_amount": gross_amount,
            "consignment_percentage": pct,
            "owner_payout_amount": payout_amount,
            "calculation_snapshot": sanitized_snapshot,
        }


# --------------------------------------------------------------------------
# Owner statements computed from real rentals (never from caller-supplied
# amounts). A consigned unit is a Serial No whose cortex_consignment_owner is
# set; its revenue is the per-unit net amount of each rental line it served
# on, for rentals returned or closed within the period.
# --------------------------------------------------------------------------

import calendar as _calendar
import json as _json
from typing import List as _List

FINISHED_STATES = ("Returned", "Closed", "Quarantine", "Disputed")
SNAPSHOT_VERSION = "cortex.owner_statement.v2"


def period_bounds(period: str):
    """'2026-09' -> ('2026-09-01', '2026-09-30')."""
    year, month = (int(part) for part in period.split("-")[:2])
    last = _calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last:02d}"


def owner_serials(company: str, owner: str) -> _List[str]:
    return frappe.get_all("Serial No", filters={"company": company, "cortex_consignment_owner": owner}, pluck="name")


def statement_lines(company: str, owner: str, period: str) -> _List[Dict[str, Any]]:
    start, end = period_bounds(period)
    serials = set(owner_serials(company, owner))
    if not serials:
        return []
    percentage = float(frappe.db.get_value("Consignment Owner", owner, "default_percentage") or 0)
    rows = frappe.db.sql(
        """
        SELECT t.name AS rental, t.starts_at, t.ends_at, t.final_invoice,
               ti.item_code, ti.item_name, ti.qty, ti.rate, ti.billable_days, ti.amount,
               ti.assigned_serials, ti.serial_no
        FROM `tabCortex Rental Transaction Item` ti
        JOIN `tabCortex Rental Transaction` t ON t.name = ti.parent
        WHERE t.company = %(company)s AND t.rental_state IN %(states)s
          AND DATE(t.ends_at) BETWEEN %(start)s AND %(end)s
        ORDER BY t.ends_at ASC
        """,
        {"company": company, "states": FINISHED_STATES, "start": start, "end": end},
        as_dict=True,
    )
    lines = []
    for row in rows:
        try:
            assigned = _json.loads(row.assigned_serials or "[]") or []
        except (TypeError, ValueError):
            assigned = []
        if row.serial_no and row.serial_no not in assigned:
            assigned.append(row.serial_no)
        qty = float(row.qty or 0) or 1.0
        per_unit_net = round(float(row.amount or 0) / qty, 2)
        per_unit_gross = round(float(row.rate or 0) * float(row.billable_days or 0), 2)
        for serial in assigned:
            if serial not in serials:
                continue
            lines.append(
                {
                    "serial_number": serial,
                    "equipment_name": row.item_name or row.item_code,
                    "rental_start_date": str(row.starts_at)[:10],
                    "rental_end_date": str(row.ends_at)[:10],
                    "billable_days": float(row.billable_days or 0),
                    "rate": float(row.rate or 0),
                    "discount_amount": round(max(0.0, per_unit_gross - per_unit_net), 2),
                    "consignment_percentage": percentage,
                    "owner_amount": round(per_unit_net * percentage / 100.0, 2),
                    "invoice_reference": row.final_invoice or "",
                    "_net": per_unit_net,
                }
            )
    return lines


def owner_statement(company: str, owner: str, period: str) -> Dict[str, Any]:
    """The owner-facing statement: allowlisted fields only (OwnerStatementSafe)."""
    record = frappe.db.get_value(
        "Consignment Owner", owner, ["name", "owner_name", "short_code", "company"], as_dict=True
    )
    if not record or record.company != company:
        frappe.throw("Propriétaire introuvable pour la société active.", frappe.PermissionError)
    start, end = period_bounds(period)
    lines = statement_lines(company, owner, period)
    net = round(sum(line["_net"] for line in lines), 2)
    due = round(sum(line["owner_amount"] for line in lines), 2)
    for line in lines:
        line.pop("_net", None)
    statement = {
        "owner": {"id": record.name, "display_name": record.owner_name, "code": record.short_code},
        "period": {"start": start, "end": end, "timezone": frappe.utils.get_system_timezone()},
        "currency": frappe.db.get_value("Company", company, "default_currency"),
        "totals": {"eligible_net_revenue": net, "owner_amount_due": due},
        "lines": lines,
        "generated_at": str(frappe.utils.now_datetime()),
        "snapshot_version": SNAPSHOT_VERSION,
    }
    return ConsignmentService._strip_forbidden_keys(statement)


def statement_status(company: str, owner: str, period: str) -> str:
    statuses = set(
        frappe.get_all(
            "Consignment Payout",
            filters={"company": company, "consignment_owner": owner, "period": period, "status": ["!=", "Cancelled"]},
            pluck="status",
        )
    )
    if not statuses:
        return "not_prepared"
    if statuses == {"Paid"}:
        return "paid"
    if statuses <= {"Approved", "Paid"}:
        return "approved"
    return "draft"


def prepare_statement(company: str, owner: str, period: str, actor: str) -> Dict[str, Any]:
    """One Consignment Payout per serial for the period (idempotent while still Calculated)."""
    lines = statement_lines(company, owner, period)
    if statement_status(company, owner, period) in ("approved", "paid"):
        frappe.throw("Ce relevé est déjà approuvé : il ne peut plus être recalculé.", frappe.ValidationError)
    for existing in frappe.get_all(
        "Consignment Payout",
        filters={"company": company, "consignment_owner": owner, "period": period, "status": "Calculated"},
        pluck="name",
    ):
        frappe.delete_doc("Consignment Payout", existing, ignore_permissions=True)
    by_serial: Dict[str, Dict[str, Any]] = {}
    for line in lines:
        entry = by_serial.setdefault(
            line["serial_number"],
            {
                "gross": 0.0,
                "discount": 0.0,
                "net": 0.0,
                "payout": 0.0,
                "days": 0.0,
                "pct": line["consignment_percentage"],
            },
        )
        entry["gross"] += line["rate"] * line["billable_days"]
        entry["discount"] += line["discount_amount"]
        entry["net"] += line["_net"]
        entry["payout"] += line["owner_amount"]
        entry["days"] += line["billable_days"]
    created = []
    for serial, entry in by_serial.items():
        snapshot = ConsignmentService.sanitize_snapshot(
            {
                "serial_no": serial,
                "days": entry["days"],
                "rate": round(entry["gross"] / entry["days"], 2) if entry["days"] else 0,
                "gross_amount": round(entry["net"], 2),
                "consignment_percentage": entry["pct"],
                "payout_amount": round(entry["payout"], 2),
                "metadata": {"period": period, "snapshot_version": SNAPSHOT_VERSION},
            }
        )
        doc = frappe.get_doc(
            {
                "doctype": "Consignment Payout",
                "company": company,
                "consignment_owner": owner,
                "period": period,
                "serial_no": serial,
                "status": "Calculated",
                "gross_amount": round(entry["net"], 2),
                "discount_amount": round(entry["discount"], 2),
                "net_amount": round(entry["net"], 2),
                "consignment_percentage": entry["pct"],
                "owner_payout_amount": round(entry["payout"], 2),
                "calculation_snapshot": _json.dumps(snapshot),
            }
        )
        doc.insert(ignore_permissions=True)
        created.append(doc.name)
    return {"payouts": created, "status": statement_status(company, owner, period)}


def set_statement_status(company: str, owner: str, period: str, target: str, reference: str = None) -> str:
    source = {"Approved": "Calculated", "Paid": "Approved"}[target]
    names = frappe.get_all(
        "Consignment Payout",
        filters={"company": company, "consignment_owner": owner, "period": period, "status": source},
        pluck="name",
    )
    if not names:
        frappe.throw("Aucun versement dans l’état attendu pour ce relevé.", frappe.ValidationError)
    for name in names:
        values = {"status": target}
        if target == "Paid":
            values.update({"paid_at": frappe.utils.now_datetime(), "payment_reference": (reference or "")[:140]})
        frappe.db.set_value("Consignment Payout", name, values)
    return statement_status(company, owner, period)
