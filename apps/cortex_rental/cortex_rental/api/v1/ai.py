"""AI Inbox, AI Workspace and AI Audit (human staff, tenant-scoped).

One queue for everything an agent produced that a person must look at:
approval requests, inbound requests with their extraction, and quote drafts
created by an agent. Confidence values come from the extraction run as
recorded; they are model scores, flagged `calibrated: false`, never
invented or rescaled here.
"""

import json
from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services.audit import AuditService

APPROVER_ROLES = {"System Manager", "Administrator", "Rental Manager", "Cortex Account Reviewer"}
TELEMETRY_ROLES = {"System Manager", "Administrator", "Cortex System Manager", "Cortex Operations Manager", "Auditor"}
OPEN_INBOUND = ("Received", "Processing")
KINDS = ("approval", "inbound", "draft")


def _json(value: Any, default: Any) -> Any:
    if not value:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _customer_name(customer: Optional[str]) -> str:
    if not customer:
        return ""
    return frappe.db.get_value("Customer", customer, "customer_name") or customer


def _latest_extraction(company: str, inbound: str):
    rows = frappe.get_all(
        "Cortex Extraction Run",
        filters={"company": company, "inbound_request": inbound},
        fields=[
            "name",
            "schema_version",
            "extracted_payload",
            "validation_status",
            "validation_errors",
            "overall_confidence",
            "review_required",
            "model_used",
            "actor_id",
            "extracted_at",
            "evidence_references",
        ],
        order_by="extracted_at desc",
        limit_page_length=1,
    )
    return rows[0] if rows else None


def _missing_fields(payload: Dict[str, Any]) -> List[str]:
    missing = []
    customer = payload.get("customer") or {}
    period = payload.get("rental_period") or {}
    if not customer.get("name"):
        missing.append("customer.name")
    if not (customer.get("email") or customer.get("phone")):
        missing.append("customer.contact")
    if not period.get("starts_at"):
        missing.append("rental_period.starts_at")
    if not period.get("ends_at"):
        missing.append("rental_period.ends_at")
    if not payload.get("items"):
        missing.append("items")
    for index, item in enumerate(payload.get("items") or []):
        if not item.get("matched_item_id") and not item.get("matched_item_code"):
            missing.append(f"items[{index}].match")
    return missing


def _inbound_state(extraction) -> str:
    if not extraction:
        return "processing"
    if extraction.validation_status == "Invalid":
        return "extraction_error"
    confidence = extraction.overall_confidence
    if confidence is not None and float(confidence) < 0.7:
        return "low_confidence"
    return "needs_review" if extraction.review_required else "ready"


def _approval_row(doc) -> Dict[str, Any]:
    customer = ""
    if doc.entity_type == "Cortex Rental Transaction":
        customer = _customer_name(frappe.db.get_value("Cortex Rental Transaction", doc.entity_id, "customer"))
    state = {"Pending": "needs_review", "Approved": "validated", "Rejected": "rejected", "Expired": "expired"}.get(
        doc.status, "needs_review"
    )
    return {
        "id": f"approval:{doc.name}",
        "kind": "approval",
        "source_id": doc.name,
        "title": doc.action,
        "summary": doc.rationale if hasattr(doc, "rationale") and doc.rationale else (doc.decision_reason or ""),
        "reference": f"{doc.entity_type} {doc.entity_id}",
        "customer": customer,
        "agent": doc.requested_by_id if doc.requested_by_type == "Agent" else None,
        "requested_by": doc.requested_by_id,
        "requested_by_type": doc.requested_by_type,
        "state": state,
        "confidence": None,
        "priority": "high" if "contract" in (doc.action or "").lower() else "normal",
        "created_at": str(doc.creation),
    }


def list_inbox_handler(company: str, kind: Optional[str], include_closed: bool, roles: set) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    if kind in (None, "approval") and roles & APPROVER_ROLES:
        filters: Dict[str, Any] = {"company": company}
        if not include_closed:
            filters["status"] = "Pending"
        for name in frappe.get_list(
            "Approval Request", filters=filters, pluck="name", order_by="creation desc", limit_page_length=200
        ):
            rows.append(_approval_row(frappe.get_doc("Approval Request", name)))

    if kind in (None, "inbound"):
        filters = {"company": company}
        if not include_closed:
            filters["status"] = ["in", list(OPEN_INBOUND)]
        for inbound in frappe.get_list(
            "Cortex Inbound Request",
            filters=filters,
            fields=["name", "source_channel", "sender_email", "subject", "status", "creation", "extracted_transaction"],
            order_by="creation desc",
            limit_page_length=200,
        ):
            extraction = _latest_extraction(company, inbound.name)
            payload = _json(extraction.extracted_payload, {}) if extraction else {}
            customer = payload.get("customer") or {}
            state = _inbound_state(extraction)
            if inbound.status == "Rejected":
                state = "rejected"
            elif inbound.status == "Processed":
                state = "applied"
            rows.append(
                {
                    "id": f"inbound:{inbound.name}",
                    "kind": "inbound",
                    "source_id": inbound.name,
                    "title": inbound.subject or inbound.name,
                    "summary": ", ".join(_missing_fields(payload)) if extraction else "",
                    "reference": inbound.source_channel,
                    "customer": customer.get("company_name") or customer.get("name") or inbound.sender_email or "",
                    "agent": extraction.actor_id if extraction else None,
                    "requested_by": inbound.sender_email,
                    "requested_by_type": "External",
                    "state": state,
                    "confidence": float(extraction.overall_confidence)
                    if extraction and extraction.overall_confidence is not None
                    else None,
                    "priority": "high" if state in ("low_confidence", "extraction_error") else "normal",
                    "created_at": str(inbound.creation),
                }
            )

    if kind in (None, "draft"):
        events = frappe.get_all(
            "Audit Event",
            filters={
                "company": company,
                "actor_type": "Agent",
                "action": "cortex.rental_transaction.draft_created",
                "entity_type": "Cortex Rental Transaction",
            },
            fields=["entity_id", "actor_id", "creation", "evidence"],
            order_by="creation desc",
            limit_page_length=200,
        )
        for event in events:
            rental = frappe.db.get_value(
                "Cortex Rental Transaction",
                event.entity_id,
                ["name", "customer", "rental_state", "grand_total", "company"],
                as_dict=True,
            )
            if not rental or rental.company != company:
                continue
            if rental.rental_state != "Quote" and not include_closed:
                continue
            rows.append(
                {
                    "id": f"draft:{rental.name}",
                    "kind": "draft",
                    "source_id": rental.name,
                    "title": rental.name,
                    "summary": "",
                    "reference": "Cortex Rental Transaction",
                    "customer": _customer_name(rental.customer),
                    "agent": event.actor_id,
                    "requested_by": event.actor_id,
                    "requested_by_type": "Agent",
                    "state": "ready" if rental.rental_state == "Quote" else "applied",
                    "confidence": None,
                    "priority": "normal",
                    "created_at": str(event.creation),
                    "amount": float(rental.grand_total or 0),
                }
            )

    rows.sort(key=lambda row: row["created_at"], reverse=True)
    return rows


if frappe:

    @frappe.whitelist(methods=["GET"])
    def list_inbox(kind: str = None, include_closed: int = 0):
        require_human_staff_role()
        company = get_company_context()
        if kind and kind not in KINDS:
            frappe.throw("Type d’élément inconnu.", frappe.ValidationError)
        roles = set(frappe.get_roles(frappe.session.user))
        items = list_inbox_handler(company, kind, bool(int(include_closed or 0)), roles)
        return {
            "data": {
                "items": items,
                "can_decide_approvals": bool(roles & APPROVER_ROLES),
                "team_scope_available": False,
            }
        }

    @frappe.whitelist(methods=["GET"])
    def get_inbox_item(kind: str, source_id: str):
        require_human_staff_role()
        company = get_company_context()
        roles = set(frappe.get_roles(frappe.session.user))

        if kind == "inbound":
            inbound = frappe.get_doc("Cortex Inbound Request", source_id)
            if inbound.company != company:
                frappe.throw("Élément introuvable.", frappe.PermissionError)
            extraction = _latest_extraction(company, inbound.name)
            payload = _json(extraction.extracted_payload, {}) if extraction else {}
            evidence = frappe.get_all(
                "Cortex Evidence Reference",
                filters={"company": company, "inbound_request": inbound.name},
                fields=["name", "source_channel", "text_excerpt", "sha256_hash", "mime_type", "scanned_clean", "file"],
                order_by="creation asc",
            )
            return {
                "data": {
                    "kind": "inbound",
                    "id": inbound.name,
                    "status": inbound.status,
                    "subject": inbound.subject or "",
                    "sender_email": inbound.sender_email or "",
                    "source_channel": inbound.source_channel,
                    "received_at": str(inbound.creation),
                    "raw_text": (inbound.raw_payload or "")[:20000],
                    "extracted_transaction": inbound.extracted_transaction,
                    "evidence": [
                        {
                            "id": e.name,
                            "channel": e.source_channel,
                            "excerpt": e.text_excerpt or "",
                            "sha256": e.sha256_hash,
                            "mime_type": e.mime_type,
                            "scanned_clean": bool(e.scanned_clean),
                            "has_file": bool(e.file),
                        }
                        for e in evidence
                    ],
                    "extraction": None
                    if not extraction
                    else {
                        "id": extraction.name,
                        "schema_version": extraction.schema_version,
                        "validation_status": extraction.validation_status,
                        "validation_errors": _json(extraction.validation_errors, []),
                        "overall_confidence": float(extraction.overall_confidence)
                        if extraction.overall_confidence is not None
                        else None,
                        "calibrated": False,
                        "review_required": bool(extraction.review_required),
                        "model": extraction.model_used,
                        "agent": extraction.actor_id,
                        "extracted_at": str(extraction.extracted_at),
                        "payload": payload,
                        "missing_fields": _missing_fields(payload),
                    },
                }
            }

        if kind == "draft":
            from cortex_rental.api.v1.rentals import _owned_transaction, _serialize

            return {"data": {"kind": "draft", "rental": _serialize(_owned_transaction(source_id, company))}}

        if kind == "approval":
            if not roles & APPROVER_ROLES:
                frappe.throw("Votre rôle ne permet pas de consulter les approbations.", frappe.PermissionError)
            doc = frappe.get_doc("Approval Request", source_id)
            if doc.company != company:
                frappe.throw("Élément introuvable.", frappe.PermissionError)
            current = {}
            if doc.entity_type == "Cortex Rental Transaction" and frappe.db.exists(doc.entity_type, doc.entity_id):
                current = (
                    frappe.db.get_value(
                        doc.entity_type,
                        doc.entity_id,
                        ["rental_state", "customer_account_ready", "insurance_ready", "payment_ready", "grand_total"],
                        as_dict=True,
                    )
                    or {}
                )
            return {
                "data": {
                    "kind": "approval",
                    "row": _approval_row(doc),
                    "status": doc.status,
                    "entity_type": doc.entity_type,
                    "entity_id": doc.entity_id,
                    "proposed": _json(doc.proposed_payload, {}),
                    "current": dict(current),
                    "evidence_ids": _json(doc.evidence_ids, []),
                    "policy_decision": _json(doc.policy_decision, {}),
                    "decided_by": doc.decided_by,
                    "decided_at": str(doc.decided_at) if doc.decided_at else None,
                    "decision_reason": doc.decision_reason,
                    "self_requested": doc.requested_by_type == "Human" and doc.requested_by_id == frappe.session.user,
                }
            }

        frappe.throw("Type d’élément inconnu.", frappe.ValidationError)

    @frappe.whitelist(methods=["POST"])
    def reject_inbound(source_id: str, reason: str):
        require_human_staff_role()
        company = get_company_context()
        if not reason or len(reason.strip()) < 3:
            frappe.throw("Un motif d’au moins trois caractères est obligatoire.", frappe.ValidationError)
        inbound = frappe.get_doc("Cortex Inbound Request", source_id)
        if inbound.company != company:
            frappe.throw("Élément introuvable.", frappe.PermissionError)
        before = inbound.status
        frappe.db.set_value(
            "Cortex Inbound Request", inbound.name, {"status": "Rejected", "processed_by": frappe.session.user}
        )
        AuditService.record_mutation(
            company=company,
            action="cortex.inbound.rejected",
            entity_type="Cortex Inbound Request",
            entity_id=inbound.name,
            before_state={"status": before},
            after_state={"status": "Rejected", "reason": reason.strip()[:500]},
        )
        return {"data": {"status": "Rejected"}}

    @frappe.whitelist(methods=["POST"])
    def link_inbound_to_rental(source_id: str, rental: str):
        """Mark an inbound request processed once a person created the quote from it."""
        require_human_staff_role()
        company = get_company_context()
        inbound = frappe.get_doc("Cortex Inbound Request", source_id)
        if inbound.company != company or frappe.db.get_value("Cortex Rental Transaction", rental, "company") != company:
            frappe.throw("Élément introuvable.", frappe.PermissionError)
        frappe.db.set_value(
            "Cortex Inbound Request",
            inbound.name,
            {"status": "Processed", "extracted_transaction": rental, "processed_by": frappe.session.user},
        )
        AuditService.record_mutation(
            company=company,
            action="cortex.inbound.converted",
            entity_type="Cortex Inbound Request",
            entity_id=inbound.name,
            after_state={"rental": rental},
        )
        return {"data": {"status": "Processed", "rental": rental}}

    @frappe.whitelist(methods=["GET"])
    def list_agent_activity(
        agent: str = None, status: str = None, from_date: str = None, to_date: str = None, page=1, page_size=50
    ):
        require_human_staff_role()
        if not set(frappe.get_roles(frappe.session.user)) & TELEMETRY_ROLES:
            frappe.throw("Votre rôle ne permet pas de consulter l’activité des agents.", frappe.PermissionError)
        company = get_company_context()
        page, page_size = max(1, int(page)), min(200, max(1, int(page_size)))
        filters: Dict[str, Any] = {"company": company}
        if agent:
            filters["agent_id"] = agent
        if status:
            filters["status"] = status
        if from_date or to_date:
            filters["started_at"] = ["between", [from_date or "1900-01-01", f"{to_date or '2999-12-31'} 23:59:59"]]
        runs = frappe.get_all(
            "Cortex Agent Run",
            filters=filters,
            fields=[
                "name",
                "agent_id",
                "request_id",
                "actor_id",
                "model_used",
                "status",
                "tool_call_count",
                "started_at",
                "last_seen_at",
            ],
            order_by="started_at desc",
            start=(page - 1) * page_size,
            page_length=page_size,
        )
        total = frappe.db.count("Cortex Agent Run", filters)
        names = [run.name for run in runs]
        calls: Dict[str, List[Dict[str, Any]]] = {}
        if names:
            for call in frappe.get_all(
                "Cortex Agent Tool Call",
                filters={"agent_run": ["in", names]},
                fields=["agent_run", "tool_name", "scope", "status", "started_at", "duration_ms", "error_message"],
                order_by="started_at asc",
            ):
                calls.setdefault(call.agent_run, []).append(
                    {
                        "tool_name": call.tool_name,
                        "scope": call.scope,
                        "status": call.status,
                        "started_at": str(call.started_at),
                        "duration_ms": call.duration_ms,
                        "error": call.error_message or None,
                    }
                )
        agents = sorted(set(frappe.get_all("Cortex Agent Run", filters={"company": company}, pluck="agent_id")))
        return {
            "data": {
                "items": [
                    {
                        "id": run.name,
                        "agent": run.agent_id,
                        "request_id": run.request_id,
                        "actor": run.actor_id,
                        "model": run.model_used or None,
                        "status": run.status,
                        "tool_call_count": int(run.tool_call_count or 0),
                        "started_at": str(run.started_at),
                        "last_seen_at": str(run.last_seen_at) if run.last_seen_at else None,
                        "tool_calls": calls.get(run.name, []),
                    }
                    for run in runs
                ],
                "total_count": total,
                "page": page,
                "page_size": page_size,
                "agents": agents,
            }
        }
