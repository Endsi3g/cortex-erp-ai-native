import json
from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.cortex_rental.doctype.audit_event.audit_event import log_audit_event
from cortex_rental.pricing import compute_billable_days

def create_draft_handler(data: Dict[str, Any], company: str, user: str) -> Dict[str, Any]:
    """
    Core business logic for quote draft creation.
    """
    starts_at = data.get("starts_at")
    ends_at = data.get("ends_at")
    customer_id = data.get("customer_id")
    lines_input = data.get("lines", [])
    evidence_ids = data.get("evidence_ids", [])
    notes = data.get("notes")

    calendar_days, billable_days = compute_billable_days(starts_at, ends_at, company)

    subtotal = 0.0
    prepared_lines = []

    for line in lines_input:
        qty = float(line.get("quantity", 1.0))
        unit_rate = float(line.get("unit_rate", 1500.0))
        discount_pct = float(line.get("discount_percentage", 0.0))

        line_subtotal = round(qty * unit_rate * billable_days, 2)
        discount_amount = round(line_subtotal * (discount_pct / 100.0), 2)
        line_total = round(line_subtotal - discount_amount, 2)

        subtotal += line_total
        prepared_lines.append({
            "item_id": line.get("item_id"),
            "quantity": qty,
            "unit_rate": unit_rate,
            "calendar_days": calendar_days,
            "billable_days": billable_days,
            "discount_percentage": discount_pct,
            "discount_amount": discount_amount,
            "total": line_total
        })

    quote_id = f"QUO-2026-{calendar_days:02d}D"

    # Write audit event
    log_audit_event(
        company=company,
        actor_type="Agent",
        actor_id=user,
        action="rental.quote.draft_created",
        entity_type="Quotation",
        entity_id=quote_id,
        evidence=evidence_ids,
        policy_decision={"policy": "QuoteDraftCreationPolicy", "decision": "allowed"},
        after_state={
            "id": quote_id,
            "state": "quote",
            "subtotal": subtotal,
            "total": subtotal,
            "lines_count": len(prepared_lines),
            "inventory_blocked": False
        }
    )

    return {
        "id": quote_id,
        "number": quote_id,
        "company_id": company,
        "customer_id": customer_id,
        "state": "quote",
        "starts_at": starts_at,
        "ends_at": ends_at,
        "calendar_days": calendar_days,
        "billable_days": billable_days,
        "subtotal": f"{subtotal:.2f}",
        "total": f"{subtotal:.2f}",
        "customer_account_ready": False,
        "insurance_ready": False,
        "payment_ready": False,
        "lines": prepared_lines,
        "notes": notes
    }

if frappe:
    @frappe.whitelist(methods=["POST"])
    def create_draft():
        data = frappe.local.form_dict
        company = frappe.local.request.headers.get("X-Company-ID") or frappe.defaults.get_user_default("Company")
        user = frappe.session.user
        result = create_draft_handler(data, company, user)
        return result
