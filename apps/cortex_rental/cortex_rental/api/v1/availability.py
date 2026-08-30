from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.availability import AvailabilityService
from cortex_rental.services.audit import AuditService


def check_availability_handler(payload: Dict[str, Any], company: str) -> List[Dict[str, Any]]:
    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    item_requests = payload.get("items") or payload.get("item_requests") or []

    svc = AvailabilityService()
    results = svc.check(
        company=company,
        starts_at=starts_at,
        ends_at=ends_at,
        item_requests=item_requests
    )
    return results


if frappe:
    @frappe.whitelist(methods=["POST"])
    def check_availability():
        require_agent_scope("agent:availability:read")
        company = get_company_context()
        payload = frappe.local.form_dict
        results = check_availability_handler(payload=payload, company=company)
        AuditService.record_read(
            action="cortex.availability.checked",
            metadata={"item_count": len(results)},
            company=company
        )
        return {"data": results, "meta": {"company": company}}
