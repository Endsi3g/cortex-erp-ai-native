from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.evidence import register_evidence
from cortex_rental.services.extraction import record_extraction_run
from cortex_rental.services.agent_telemetry import log_tool_call
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency


def register_evidence_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    return register_evidence(
        company=company,
        source_channel=payload.get("source_channel") or "other",
        actor_id=actor_id,
        inbound_request=payload.get("inbound_request"),
        file_name=payload.get("file_name"),
        text_excerpt=payload.get("text_excerpt"),
    )


def record_extraction_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    return record_extraction_run(
        company=company,
        actor_id=actor_id,
        extracted_payload=payload.get("extracted_payload") or {},
        model_used=payload.get("model_used"),
        inbound_request=payload.get("inbound_request"),
        evidence_ids=payload.get("evidence_ids") or [],
    )


if frappe:

    @frappe.whitelist(methods=["POST"])
    @log_tool_call("register_evidence", scope="agent:intake:evidence")
    def register_evidence_api():
        require_agent_scope("agent:intake:evidence")
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="intake.register_evidence",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: register_evidence_handler(payload=payload, company=company, actor_id=frappe.session.user),
        )
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    @log_tool_call("record_structured_extraction", scope="agent:intake:extract")
    def record_extraction():
        require_agent_scope("agent:intake:extract")
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="intake.record_extraction",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: record_extraction_handler(payload=payload, company=company, actor_id=frappe.session.user),
        )
        return {"data": result, "meta": {"company": company}}
