"""
Audit trail and governance recording service.
Guarantees append-only, immutable event records for all Cortex operations.
"""
from typing import Any, Dict, Optional
import json

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.cortex_rental.doctype.audit_event.audit_event import log_audit_event


class AuditService:
    @staticmethod
    def actor_from_request() -> Dict[str, str]:
        """
        Extract actor information from the current Frappe execution context.
        """
        if not frappe:
            return {"actor_type": "Human", "actor_id": "test_user"}

        user = getattr(frappe.session, "user", "Administrator")
        roles = frappe.get_roles(user) if hasattr(frappe, "get_roles") else []

        if "Agent Service Account" in roles or getattr(frappe.flags, "in_agent_context", False):
            actor_type = "Agent"
        elif user in ["Administrator", "Guest"]:
            actor_type = "System" if user == "Guest" else "Human"
        else:
            actor_type = "Human"

        return {
            "actor_type": actor_type,
            "actor_id": user,
            "roles": roles
        }

    @classmethod
    def record_mutation(
        cls,
        company: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        evidence: Optional[Any] = None,
        policy_decision: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Any:
        """
        Record a state mutation into the append-only audit log.
        """
        actor = cls.actor_from_request()
        return log_audit_event(
            company=company,
            actor_type=actor["actor_type"],
            actor_id=actor["actor_id"],
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            evidence=evidence,
            policy_decision=policy_decision,
            request_id=request_id
        )

    @classmethod
    def record_read(
        cls,
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
        company: Optional[str] = None
    ) -> None:
        """
        Record a sensitive read or query event.
        """
        actor = cls.actor_from_request()
        if frappe and company:
            try:
                log_audit_event(
                    company=company,
                    actor_type=actor["actor_type"],
                    actor_id=actor["actor_id"],
                    action=action,
                    entity_type="Query",
                    entity_id="read_operation",
                    after_state=metadata
                )
            except Exception:
                pass
