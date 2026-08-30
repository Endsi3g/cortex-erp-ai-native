from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.pricing import PricingService
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency
from cortex_rental.services.agent_telemetry import log_tool_call


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

        processed_lines.append(
            {
                "item_code": item_id,
                "qty": qty,
                "rate": unit_rate,
                "calendar_days": calendar_days,
                "billable_days": billable_days,
                "discount_percentage": discount,
                "amount": line_amount,
            }
        )

    tx_name = f"CR-TRX-2026-{frappe.utils.now_datetime().strftime('%s')[-5:]}" if frappe else "CR-TRX-2026-00001"

    if frappe:
        doc = frappe.get_doc(
            {
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
                "items": processed_lines,
            }
        )
        doc.insert(ignore_permissions=True)
        tx_name = doc.name

    AuditService.record_mutation(
        company=company,
        action="cortex.rental_transaction.draft_created",
        entity_type="Cortex Rental Transaction",
        entity_id=tx_name,
        evidence=payload.get("evidence_ids"),
        after_state={"id": tx_name, "state": "quote", "total": f"{total_amount:.2f}", "billable_days": billable_days},
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
        "items_count": len(processed_lines),
    }


def preview_pricing_handler(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    """
    Read-only counterpart to create_draft_handler: same PricingService
    calls, no Cortex Rental Transaction ever created. Exists so the
    Transaction Composer frontend can show a live price preview while
    the user is still editing lines, without either creating a real
    (throwaway) draft per keystroke or re-implementing the billable-days
    curve in JavaScript — the design system explicitly forbids the
    latter ("Le prix est présenté comme résultat du PricingService, pas
    comme calcul frontend").

    Unlike create_draft_handler, a missing unit_rate defaults to 0.0,
    not a fabricated 100.0 — a preview silently showing a fake $100/day
    would be worse than showing $0 and making the missing rate obvious.
    """
    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    if not starts_at or not ends_at:
        raise ValueError("starts_at and ends_at are required.")

    lines = payload.get("lines") or []
    calendar_days, billable_days = PricingService.compute_billable_days(starts_at, ends_at, company)

    total_amount = 0.0
    processed_lines = []
    for line in lines:
        qty = float(line.get("quantity") or 1.0)
        unit_rate = float(line.get("unit_rate") or 0.0)
        discount = float(line.get("discount_percentage") or 0.0)
        line_amount = PricingService.calculate_line_total(unit_rate, qty, billable_days, discount)
        total_amount += line_amount
        processed_lines.append(
            {
                "item_id": line.get("item_id"),
                "quantity": qty,
                "unit_rate": unit_rate,
                "discount_percentage": discount,
                "amount": f"{line_amount:.2f}",
            }
        )

    return {
        "calendar_days": calendar_days,
        "billable_days": billable_days,
        "subtotal": f"{total_amount:.2f}",
        "total": f"{total_amount:.2f}",
        "lines": processed_lines,
    }


if frappe:

    @frappe.whitelist(methods=["POST"])
    @log_tool_call("preview_pricing", scope="agent:quote:draft")
    def preview_pricing():
        require_agent_scope("agent:quote:draft")
        company = get_company_context()
        payload = frappe.local.form_dict
        lines = payload.get("lines")
        if isinstance(lines, str):
            payload = dict(payload)
            payload["lines"] = frappe.parse_json(lines)
        result = preview_pricing_handler(payload=payload, company=company)
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    @log_tool_call("create_quote_draft", scope="agent:quote:draft")
    def create_quote_draft():
        require_agent_scope("agent:quote:draft")
        company = get_company_context()
        payload = frappe.local.form_dict
        # `lines` arrives as a JSON string when called from a browser
        # (frappe.call form-encodes args), but as a real list when
        # called in-process from MCP/tests — handle both rather than
        # assuming one caller shape.
        if isinstance(payload.get("lines"), str):
            payload = dict(payload)
            payload["lines"] = frappe.parse_json(payload["lines"])
        result = with_idempotency(
            company=company,
            scope="quotes.create_quote_draft",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: create_draft_handler(payload=payload, company=company, actor_id=frappe.session.user),
        )
        return {"data": result, "meta": {"company": company}}
