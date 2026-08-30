import json
from typing import Any, Dict, Optional

try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    # Standalone test/mock fallback
    class Document:
        pass

    frappe = None


class AuditEvent(Document):
    """
    Append-only, immutable audit trail for all Cortex mutations.
    Strictly forbids update and delete operations.
    """

    def before_save(self):
        if hasattr(self, "is_new") and not self.is_new():
            if frappe:
                frappe.throw("Audit events are strictly immutable and cannot be modified.", frappe.PermissionError)
            else:
                raise PermissionError("Audit events are strictly immutable.")

    def on_trash(self):
        if frappe:
            frappe.throw("Audit events are permanent and cannot be deleted.", frappe.PermissionError)
        else:
            raise PermissionError("Audit events cannot be deleted.")


def log_audit_event(
    company: str,
    actor_type: str,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    evidence: Optional[Any] = None,
    policy_decision: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Any:
    """
    Helper function to atomically create an immutable audit record.
    """
    payload = {
        "doctype": "Audit Event",
        "company": company,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_state": json.dumps(before_state) if before_state else None,
        "after_state": json.dumps(after_state) if after_state else None,
        "evidence": json.dumps(evidence) if evidence else None,
        "policy_decision": json.dumps(policy_decision) if policy_decision else None,
        "request_id": request_id,
    }

    if frappe:
        doc = frappe.get_doc(payload)
        doc.flags.ignore_permissions = True
        doc.insert()
        return doc
    return payload
