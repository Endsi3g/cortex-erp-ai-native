from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.pricing import PricingService
from cortex_rental.services.audit import AuditService


def create_draft_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    customer_id = payload.get("customer_id")
    lines = payload.get("lines") or []

    calendar_days, billable_days = PricingService.compute_billable_days(starts_at, ends_at, company)

    total_amount = 0.0
    processed_lines = []

    for line in lines:
        item_id = line.get("item_id")
        qty = float(line.get("quantity") or 1.0)
        unit_rate = float(line.get("unit_rate") or 100.0)
        discount = float(line.get("discount_percentage") or 0.0)
        line_amount = PricingService.calculate_line_total(unit_rate, qty, billable_days, discount)
        total_amount += line_amount

        processed_lines.append({
            "item_code": item_id,
            "qty": qty,
            "rate": unit_rate,
            "calendar_days": calendar_days,
            "billable_days": billable_days,
            "discount_percentage": discount,
            "amount": line_amount
        })

    tx_name = f"CR-TRX-2026-{frappe.utils.now_datetime().strftime('%s')[-5:]}" if frappe else "CR-TRX-2026-00001"

    if frappe:
        doc = frappe.get_doc({
            "doctype": "Cortex Rental Transaction",
            "company": company,
            "customer": customer_id,
            "rental_state": "Quote",
            "starts_at": starts_at,
            "ends_at": ends_at,
            "calendar_days": calendar_days,
            "billable_days": billable_days,
            "subtotal": total_amount,
            "grand_total": total_amount,
            "notes": payload.get("notes") or "Created by Cortex AI Intake",
            "items": processed_lines
        })
        doc.insert(ignore_permissions=True)
        tx_name = doc.name

    AuditService.record_mutation(
        company=company,
        action="cortex.rental_transaction.draft_created",
        entity_type="Cortex Rental Transaction",
        entity_id=tx_name,
        evidence=payload.get("evidence_ids"),
        after_state={
            "id": tx_name,
            "state": "quote",
            "total": f"{total_amount:.2f}",
            "billable_days": billable_days
        }
    )

    return {
        "id": tx_name,
        "state": "quote",
        "customer_id": customer_id,
        "calendar_days": calendar_days,
        "billable_days": billable_days,
        "total": f"{total_amount:.2f}",
        "customer_account_ready": False,
        "insurance_ready": False,
        "payment_ready": False,
        "items_count": len(processed_lines)
    }


if frappe:
    @frappe.whitelist(methods=["POST"])
    def create_quote_draft():
        require_agent_scope("agent:quote:draft")
        company = get_company_context()
        payload = frappe.local.form_dict
        result = create_draft_handler(payload=payload, company=company, actor_id=frappe.session.user)
        return {"data": result, "meta": {"company": company}}
