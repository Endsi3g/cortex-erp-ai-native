"""Read models for the AI Inbox, AI Audit and agent activity screens.

Inbound requests and AI drafts are projections of Cortex Inbound Request and
Cortex Extraction Run. A confidence the extraction did not record is returned as
null: the UI shows "confiance non évaluée", never a default score.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.api.v1._shared import MAX_RAW_TEXT, envelope, page_args, parse_json
from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role

INBOUND = "Cortex Inbound Request"
EXTRACTION = "Cortex Extraction Run"
SOURCE_MAP = {"Email": "email", "PDF Upload": "pdf", "Web Portal": "web_form", "API Intake": "web_form"}
TELEMETRY_ROLES = {"System Manager", "Administrator"}
INBOUND_FILTERS = {
    "new": {"status": ["in", ["Received", "Processing"]]},
    "reviewed": {"status": "Processed", "extracted_transaction": ["is", "not set"]},
    "converted": {"status": "Processed", "extracted_transaction": ["is", "set"]},
    "dismissed": {"status": "Rejected"},
}
DRAFT_FIELDS = [
    "name",
    "inbound_request",
    "overall_confidence",
    "review_required",
    "validation_status",
    "extracted_payload",
    "evidence_references",
    "extracted_at",
]


def _inbound_status(row: Any) -> str:
    if row.status in ("Received", "Processing"):
        return "new"
    if row.status == "Rejected":
        return "dismissed"
    return "converted" if row.get("extracted_transaction") else "reviewed"


def _missing_fields(payload: Dict[str, Any]) -> List[str]:
    missing = []
    if not (payload.get("customer") or {}).get("name"):
        missing.append("Client")
    period = payload.get("rental_period") or {}
    if not period.get("starts_at") or not period.get("ends_at"):
        missing.append("Période de location")
    if not payload.get("items"):
        missing.append("Équipement")
    return missing


def _extracted_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    period = payload.get("rental_period") or {}
    fields: Dict[str, Any] = {"missing_fields": _missing_fields(payload)}
    if (payload.get("customer") or {}).get("name"):
        fields["customer_name"] = payload["customer"]["name"]
    if period.get("starts_at"):
        fields["start_date"] = period["starts_at"]
    if period.get("ends_at"):
        fields["end_date"] = period["ends_at"]
    fields["equipment_mentions"] = [
        {
            "raw_text": item.get("raw_text", ""),
            **(
                {"matched_item_code": item.get("matched_item_id") or item.get("suggested_sku")}
                if item.get("matched_item_id") or item.get("suggested_sku")
                else {}
            ),
            "quantity": item.get("quantity"),
            "confidence": item.get("confidence"),
        }
        for item in payload.get("items") or []
    ]
    return fields


def _latest_runs(company: str, inbound_names: List[str]) -> Dict[str, Any]:
    if not inbound_names:
        return {}
    runs = frappe.get_all(
        EXTRACTION,
        filters={"company": company, "inbound_request": ["in", inbound_names]},
        fields=DRAFT_FIELDS,
        order_by="extracted_at desc",
        limit_page_length=0,
    )
    latest: Dict[str, Any] = {}
    for run in runs:
        latest.setdefault(run.inbound_request, run)
    return latest


def serialize_inbound(row: Any, run: Optional[Any]) -> Dict[str, Any]:
    payload = parse_json(run.extracted_payload, {}) if run else parse_json(row.get("structured_data"), {})
    item: Dict[str, Any] = {
        "id": row.name,
        "source": SOURCE_MAP.get(row.source_channel, "web_form"),
        "sender_email": row.sender_email or "",
        "subject": row.subject or row.name,
        "raw_body": (row.raw_payload or "")[:MAX_RAW_TEXT],
        "received_at": str(row.creation),
        "overall_confidence": run.overall_confidence if run and run.overall_confidence is not None else None,
        "extracted_fields": _extracted_fields(payload),
        "status": _inbound_status(row),
    }
    if row.get("extracted_transaction"):
        item["converted_rental_id"] = row.extracted_transaction
    return item


def list_inbound_handler(company: str, status: Optional[str], page: int, page_size: int) -> Dict[str, Any]:
    filters: Dict[str, Any] = {"company": company, **INBOUND_FILTERS.get(status or "", {})}
    total = frappe.db.count(INBOUND, filters=filters)
    rows = frappe.get_list(
        INBOUND,
        filters=filters,
        fields=[
            "name",
            "source_channel",
            "sender_email",
            "subject",
            "raw_payload",
            "structured_data",
            "status",
            "extracted_transaction",
            "creation",
        ],
        order_by="creation desc",
        start=(page - 1) * page_size,
        page_length=page_size,
    )
    runs = _latest_runs(company, [row.name for row in rows])
    return {"items": [serialize_inbound(row, runs.get(row.name)) for row in rows], "total_count": total}


def get_inbound_handler(company: str, inbound_id: str) -> Dict[str, Any]:
    rows = frappe.get_list(
        INBOUND,
        filters={"company": company, "name": inbound_id},
        fields=[
            "name",
            "source_channel",
            "sender_email",
            "subject",
            "raw_payload",
            "structured_data",
            "status",
            "extracted_transaction",
            "creation",
        ],
        page_length=1,
    )
    if not rows:
        frappe.throw("Demande entrante introuvable.", frappe.DoesNotExistError)
    return serialize_inbound(rows[0], _latest_runs(company, [inbound_id]).get(inbound_id))


def serialize_draft(run: Any, inbound: Optional[Any]) -> Dict[str, Any]:
    payload = parse_json(run.extracted_payload, {})
    target = inbound.get("extracted_transaction") if inbound else None
    if inbound and inbound.status == "Rejected":
        status = "rejected"
    elif target:
        status = "accepted"
    else:
        status = "pending_review"
    draft: Dict[str, Any] = {
        "id": run.name,
        "draft_type": "Quote Draft",
        "title": (inbound.subject if inbound and inbound.subject else run.name),
        "ai_state": "needs_confirmation" if run.review_required or run.validation_status == "Invalid" else "proposed",
        "source_evidence_id": run.inbound_request or run.name,
        "source_evidence_type": INBOUND,
        "confidence_score": run.overall_confidence if run.overall_confidence is not None else None,
        "proposed_payload": {"customer_name": (payload.get("customer") or {}).get("name"), **payload},
        "target_doctype": "Cortex Rental Transaction",
        "created_at": str(run.extracted_at) if run.extracted_at else "",
        "status": status,
    }
    if target:
        draft["target_name"] = target
    return draft


def list_drafts_handler(company: str, status: Optional[str], page: int, page_size: int) -> Dict[str, Any]:
    runs = frappe.get_list(
        EXTRACTION,
        filters={"company": company},
        fields=DRAFT_FIELDS,
        order_by="extracted_at desc",
        start=(page - 1) * page_size,
        page_length=page_size,
    )
    names = list({run.inbound_request for run in runs if run.inbound_request})
    inbound = (
        {
            row.name: row
            for row in frappe.get_all(
                INBOUND,
                filters={"company": company, "name": ["in", names]},
                fields=["name", "subject", "status", "extracted_transaction"],
            )
        }
        if names
        else {}
    )
    items = [serialize_draft(run, inbound.get(run.inbound_request)) for run in runs]
    if status:
        items = [item for item in items if item["status"] == status]
    return {"items": items, "total_count": frappe.db.count(EXTRACTION, filters={"company": company})}


def activity_handler(company: str, limit: int) -> Dict[str, Any]:
    runs = frappe.get_list(
        "Cortex Agent Run",
        filters={"company": company},
        fields=["name", "agent_id", "model_used", "status", "tool_call_count", "started_at", "last_seen_at"],
        order_by="started_at desc",
        page_length=limit,
    )
    calls: Dict[str, List[Dict[str, Any]]] = {}
    if runs:
        for call in frappe.get_all(
            "Cortex Agent Tool Call",
            filters={"agent_run": ["in", [run.name for run in runs]]},
            fields=["agent_run", "tool_name", "status", "duration_ms", "error_message"],
            limit_page_length=0,
        ):
            calls.setdefault(call.agent_run, []).append(
                {
                    "tool_name": call.tool_name,
                    "status": "success" if call.status == "Success" else "error",
                    **({"latency_ms": call.duration_ms} if call.duration_ms is not None else {}),
                    **({"error_message": call.error_message} if call.error_message else {}),
                }
            )
    return {
        "runs": [
            {
                "run_id": run.name,
                "agent_name": run.agent_id,
                "started_at": str(run.started_at) if run.started_at else "",
                **({"ended_at": str(run.last_seen_at)} if run.last_seen_at else {}),
                **({"model_used": run.model_used} if run.model_used else {}),
                "status": {"Completed": "completed", "Failed": "failed"}.get(run.status, "running"),
                "tools_invoked": calls.get(run.name, []),
            }
            for run in runs
        ],
        "total_runs": frappe.db.count("Cortex Agent Run", filters={"company": company}),
    }


def audit_handler(
    company: str,
    entity_type: Optional[str],
    entity_id: Optional[str],
    actor_id: Optional[str],
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {"company": company}
    for key, value in (("entity_type", entity_type), ("entity_id", entity_id), ("actor_id", actor_id)):
        if value:
            filters[key] = value
    total = frappe.db.count("Audit Event", filters=filters)
    rows = frappe.get_list(
        "Audit Event",
        filters=filters,
        fields=[
            "name",
            "creation",
            "actor_type",
            "actor_id",
            "action",
            "entity_type",
            "entity_id",
            "request_id",
            "before_state",
            "after_state",
            "policy_decision",
        ],
        order_by="creation desc",
        start=(page - 1) * page_size,
        page_length=page_size,
    )
    events = []
    for row in rows:
        event: Dict[str, Any] = {
            "id": row.name,
            "timestamp": str(row.creation),
            "actor": {"actor_type": row.actor_type or "System", "actor_id": row.actor_id or ""},
            "action": row.action,
            "entity_type": row.entity_type or "",
            "entity_id": row.entity_id or "",
            "request_id": row.request_id or "",
        }
        for source, target in (
            ("before_state", "before_state"),
            ("after_state", "after_state"),
            ("policy_decision", "policy_decision"),
        ):
            parsed = parse_json(row.get(source), {})
            if parsed:
                event[target] = parsed
        events.append(event)
    return {"events": events, "total_count": total}


if frappe:

    @frappe.whitelist(methods=["GET"])
    def list_inbound_requests(status: str = None, page: int = 1, page_size: int = 20):
        require_human_staff_role()
        if not frappe.has_permission(INBOUND, "read"):
            frappe.throw("Accès refusé aux demandes entrantes.", frappe.PermissionError)
        page, page_size = page_args(page, page_size)
        return envelope(list_inbound_handler(get_company_context(), status, page, page_size))

    @frappe.whitelist(methods=["GET"])
    def get_inbound_request(id: str):
        require_human_staff_role()
        if not frappe.has_permission(INBOUND, "read"):
            frappe.throw("Accès refusé aux demandes entrantes.", frappe.PermissionError)
        return envelope(get_inbound_handler(get_company_context(), id))

    @frappe.whitelist(methods=["GET"])
    def list_ai_drafts(status: str = None, page: int = 1, page_size: int = 20):
        require_human_staff_role()
        if not frappe.has_permission(EXTRACTION, "read"):
            frappe.throw("Accès refusé aux brouillons IA.", frappe.PermissionError)
        page, page_size = page_args(page, page_size)
        return envelope(list_drafts_handler(get_company_context(), status, page, page_size))

    @frappe.whitelist(methods=["GET"])
    def get_agent_activity(limit: int = 20):
        if not set(frappe.get_roles(frappe.session.user)) & TELEMETRY_ROLES:
            frappe.throw("La télémétrie des agents est réservée aux administrateurs.", frappe.PermissionError)
        return envelope(activity_handler(get_company_context(), min(100, max(1, int(limit)))))

    @frappe.whitelist(methods=["GET"])
    def list_audit_events(
        entity_type: str = None, entity_id: str = None, actor_id: str = None, page: int = 1, page_size: int = 20
    ):
        if not frappe.has_permission("Audit Event", "read"):
            frappe.throw("Accès refusé au journal d'audit.", frappe.PermissionError)
        page, page_size = page_args(page, page_size)
        return envelope(audit_handler(get_company_context(), entity_type, entity_id, actor_id, page, page_size))
