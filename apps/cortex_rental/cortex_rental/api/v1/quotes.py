from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.pricing import PricingService
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency
from cortex_rental.services.agent_telemetry import log_tool_call


def _server_rates(lines: List[Dict[str, Any]], company: str) -> Dict[str, float]:
    """Daily rates from the company's rental profiles (the only price authority)."""
    codes = sorted({line.get("item_id") or line.get("item_code") for line in lines})
    rates = {}
    for code in codes:
        rate = frappe.db.get_value("Cortex Rental Item Profile", {"company": company, "item_code": code}, "daily_rate")
        if rate is None:
            frappe.throw(f"{code} n’est pas dans le catalogue locatif de la société.", frappe.ValidationError)
        rates[code] = float(rate or 0)
    return rates


def _price_lines(lines: List[Dict[str, Any]], billable_days: float, calendar_days: int, rates: Dict[str, float]):
    """
    Price agent-requested lines. `unit_rate` sent by the caller is ignored on
    purpose: agents never set prices. Agents cannot apply discounts either.
    """
    total, processed = 0.0, []
    for line in lines:
        code = line.get("item_id") or line.get("item_code")
        qty = float(line.get("quantity") or 1.0)
        if qty <= 0:
            raise ValueError(f"Quantité invalide pour {code}.")
        if float(line.get("discount_percentage") or 0):
            raise PermissionError("Un agent ne peut pas appliquer de remise ; une personne autorisée doit le faire.")
        rate = float(rates.get(code) or 0.0)
        amount = PricingService.calculate_line_total(rate, qty, billable_days)
        total += amount
        processed.append(
            {
                "item_code": code,
                "qty": qty,
                "rate": rate,
                "calendar_days": calendar_days,
                "billable_days": billable_days,
                "discount_percentage": 0.0,
                "amount": amount,
            }
        )
    return round(total, 2), processed


def create_draft_handler(
    payload: Dict[str, Any], company: str, actor_id: str, rates: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    customer_id = payload.get("customer_id")
    lines = payload.get("lines") or []
    if not starts_at or not ends_at or not lines:
        raise ValueError("starts_at, ends_at and at least one line are required.")

    calendar_days, billable_days = PricingService.compute_billable_days(starts_at, ends_at, company)
    if frappe:
        if not frappe.db.exists("Customer", {"name": customer_id, "cortex_company": company}):
            frappe.throw("Client introuvable pour la société.", frappe.PermissionError)
        rates = _server_rates(lines, company)
    total_amount, processed_lines = _price_lines(lines, billable_days, calendar_days, rates or {})

    tx_name = "CR-TRX-DRAFT"
    if frappe:
        doc = frappe.get_doc(
            {
                "doctype": "Cortex Rental Transaction",
                "company": company,
                "customer": customer_id,
                "rental_state": "Quote",
                "starts_at": starts_at,
                "ends_at": ends_at,
                "notes": payload.get("notes") or "Brouillon créé par l’assistant de demande client",
                "items": [
                    {k: v for k, v in line.items() if k in ("item_code", "qty", "rate", "discount_percentage")}
                    for line in processed_lines
                ],
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


def preview_pricing_handler(
    payload: Dict[str, Any], company: str, rates: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Read-only counterpart of create_draft_handler: same pricing, nothing persisted."""
    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    if not starts_at or not ends_at:
        raise ValueError("starts_at and ends_at are required.")
    lines = payload.get("lines") or []
    calendar_days, billable_days = PricingService.compute_billable_days(starts_at, ends_at, company)
    if frappe and lines:
        rates = _server_rates(lines, company)
    total, processed = _price_lines(lines, billable_days, calendar_days, rates or {})
    return {
        "calendar_days": calendar_days,
        "billable_days": billable_days,
        "subtotal": f"{total:.2f}",
        "total": f"{total:.2f}",
        "lines": [
            {
                "item_id": line["item_code"],
                "quantity": line["qty"],
                "unit_rate": line["rate"],
                "discount_percentage": 0.0,
                "amount": f"{line['amount']:.2f}",
            }
            for line in processed
        ],
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
