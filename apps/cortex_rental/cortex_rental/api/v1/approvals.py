from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency


def submit_approval_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    action = payload.get("action")
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    proposed_payload = payload.get("proposed_payload")
    evidence_ids = payload.get("evidence_ids") or []
    rationale = payload.get("rationale") or payload.get("reason")

    req_id = "apr-req-mock-001"

    if frappe:
        doc = frappe.get_doc(
            {
                "doctype": "Approval Request",
                "company": company,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": "Pending",
                "proposed_payload": frappe.as_json(proposed_payload) if proposed_payload else None,
                "evidence_references": frappe.as_json(evidence_ids) if evidence_ids else None,
                "agent_rationale": rationale,
                "created_by_agent": actor_id,
            }
        )
        doc.insert(ignore_permissions=True)
        req_id = doc.name

    AuditService.record_mutation(
        company=company,
        action="cortex.approval_request.submitted",
        entity_type="Approval Request",
        entity_id=req_id,
        evidence=evidence_ids,
        after_state={"action": action, "entity_type": entity_type, "entity_id": entity_id, "status": "Pending"},
    )

    return {
        "id": req_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "status": "Pending",
        "rationale": rationale,
        "company": company,
    }


if frappe:

    @frappe.whitelist(methods=["POST"])
    def submit_approval():
        require_agent_scope("agent:approval:submit")
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="approvals.submit_approval",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: submit_approval_handler(payload=payload, company=company, actor_id=frappe.session.user),
        )
        return {"data": result, "meta": {"company": company}}
