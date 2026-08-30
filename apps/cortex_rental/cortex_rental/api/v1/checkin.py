from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_human_staff_role, get_company_context
from cortex_rental.services.checkin import complete_checkin
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency

# NOTE: no @log_tool_call / agent scope here on purpose. This endpoint
# is human-staff-only (require_human_staff_role) — it is not part of
# the agent-facing surface and has no MCP tool, so it isn't part of the
# Cortex Agent Run/Tool Call telemetry either.


def complete_checkin_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    checkin_name = payload.get("checkin_id")
    if not checkin_name:
        raise ValueError("checkin_id is required.")
    return complete_checkin(checkin_name=checkin_name, actor_id=actor_id)


if frappe:

    @frappe.whitelist(methods=["POST"])
    def complete_checkin_api():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="checkin.complete_checkin",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: complete_checkin_handler(payload=payload, company=company, actor_id=frappe.session.user),
        )
        return {"data": result, "meta": {"company": company}}
