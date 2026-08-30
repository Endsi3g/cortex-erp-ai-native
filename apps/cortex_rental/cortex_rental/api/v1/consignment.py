from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.consignment import ConsignmentService
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency


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
        metadata={"note": "Automated statement prepared via FastMCP"}
    )

    doc_id = "PAYOUT-DRAFT-001"

    if frappe:
        doc = frappe.get_doc({
            "doctype": "Consignment Payout",
            "company": company,
            "owner": owner_id,
            "gross_amount": gross_amount,
            "consignment_percentage": consignment_percentage,
            "owner_payout_amount": payout_data["owner_payout_amount"],
            "calculation_snapshot": frappe.as_json(payout_data["calculation_snapshot"])
        })
        doc.insert(ignore_permissions=True)
        doc_id = doc.name

    AuditService.record_mutation(
        company=company,
        action="cortex.consignment.statement_prepared",
        entity_type="Consignment Payout",
        entity_id=doc_id,
        after_state={"owner": owner_id, "payout_amount": payout_data["owner_payout_amount"]}
    )

    return {
        "id": doc_id,
        "owner_id": owner_id,
        "gross_amount": gross_amount,
        "consignment_percentage": consignment_percentage,
        "owner_payout_amount": payout_data["owner_payout_amount"],
        "calculation_snapshot": payout_data["calculation_snapshot"]
    }


if frappe:
    @frappe.whitelist(methods=["POST"])
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
