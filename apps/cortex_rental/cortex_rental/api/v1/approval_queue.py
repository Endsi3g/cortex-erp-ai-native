"""Tenant-scoped human review queue for persisted Approval Request DocTypes."""

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context


def _require_approver():
    roles = set(frappe.get_roles(frappe.session.user))
    if not roles.intersection({"System Manager", "Administrator", "Rental Manager", "Cortex Account Reviewer"}):
        frappe.throw("Votre rôle ne permet pas de décider une approbation.", frappe.PermissionError)


def _json(value):
    if not value:
        return []
    if isinstance(value, str):
        return frappe.parse_json(value)
    return value


def _serialize(doc):
    payload = _json(doc.proposed_payload) or {}
    action = (doc.action or "").lower()
    if "contract" in action:
        approval_type = "Contract Confirmation"
        title = "Confirmation du contrat"
    elif "discount" in action:
        approval_type = "Discount Override"
        title = "Dérogation de remise"
    else:
        approval_type = "AI Draft Execution"
        title = doc.action or "Action soumise à approbation"
    return {
        "provenance": "api",
        "last_synced_at": frappe.utils.now_datetime().isoformat(),
        "id": doc.name,
        "approval_type": approval_type,
        "status": (doc.status or "Pending").lower(),
        "title": title,
        "description": doc.decision_reason or doc.action or "Demande en attente de révision humaine.",
        "reference_doctype": doc.entity_type,
        "reference_name": doc.entity_id,
        "requested_by_type": doc.requested_by_type,
        "requested_by": doc.requested_by_id,
        "before_state": {},
        "after_state": payload,
        "evidence_ids": _json(doc.evidence_ids) or [],
        "created_at": str(doc.creation),
        "resolved_at": str(doc.decided_at) if doc.decided_at else None,
        "resolved_by": doc.decided_by,
        "rejection_reason": doc.decision_reason if doc.status == "Rejected" else None,
    }


if frappe:
    @frappe.whitelist(methods=["GET"])
    def list_approval_requests(status="pending", page=1, page_size=20):
        _require_approver()
        company = get_company_context()
        page, page_size = max(1, int(page)), min(100, max(1, int(page_size)))
        filters = {"company": company}
        if status and status != "all":
            filters["status"] = status.title()
        total = frappe.db.count("Approval Request", filters=filters)
        rows = frappe.get_all("Approval Request", filters=filters, fields=["name"],
            order_by="creation desc", start=(page - 1) * page_size, page_length=page_size)
        items = [_serialize(frappe.get_doc("Approval Request", row.name)) for row in rows]
        return {"data": {"provenance": "api",
            "last_synced_at": frappe.utils.now_datetime().isoformat(),
            "items": items, "total_count": total}}

    @frappe.whitelist(methods=["GET"])
    def get_approval_request(name: str):
        _require_approver()
        doc = frappe.get_doc("Approval Request", name)
        if doc.company != get_company_context():
            frappe.throw("Demande d’approbation introuvable.", frappe.PermissionError)
        return {"data": _serialize(doc)}

    @frappe.whitelist(methods=["POST"])
    def decide_approval(name: str, decision: str, reason: str = None):
        _require_approver()
        doc = frappe.get_doc("Approval Request", name)
        if doc.company != get_company_context():
            frappe.throw("Demande d’approbation introuvable.", frappe.PermissionError)
        decision = (decision or "").lower()
        if decision == "approve":
            doc.approve(reason=reason)
        elif decision == "reject":
            if not reason or len(reason.strip()) < 3:
                frappe.throw("Un motif de refus d’au moins trois caractères est obligatoire.", frappe.ValidationError)
            doc.reject(reason=reason)
        else:
            frappe.throw("Decision must be approve or reject.", frappe.ValidationError)
        return {"request_id": frappe.generate_hash(length=16), "entity_id": name,
            "status": "completed", "approval_required": False, "mutation_performed": True}
