from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.cortex_rental.doctype.audit_event.audit_event import log_audit_event

def submit_approval_handler(data: Dict[str, Any], company: str, user: str) -> Dict[str, Any]:
    action = data.get("action")
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")
    proposed_payload = data.get("proposed_payload", {})
    evidence_ids = data.get("evidence_ids", [])
    policy_decision = data.get("policy_decision", {})

    appr_id = f"APPR-2026-0001"

    log_audit_event(
        company=company,
        actor_type="Agent",
        actor_id=user,
        action="rental.approval.submitted",
        entity_type=entity_type,
        entity_id=entity_id,
        evidence=evidence_ids,
        policy_decision=policy_decision,
        after_state={"approval_id": appr_id, "status": "pending"}
    )

    return {
        "id": appr_id,
        "company_id": company,
        "action": action,
        "status": "pending",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "requested_by_type": "agent",
        "requested_by_id": user,
        "proposed_payload": proposed_payload,
        "evidence_ids": evidence_ids
    }

if frappe:
    @frappe.whitelist(methods=["POST"])
    def submit():
        data = frappe.local.form_dict
        company = frappe.local.request.headers.get("X-Company-ID") or frappe.defaults.get_user_default("Company")
        user = frappe.session.user
        return submit_approval_handler(data, company, user)
