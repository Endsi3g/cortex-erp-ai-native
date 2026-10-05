"""Tenant-scoped human review queue for persisted Approval Request DocTypes."""

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context


def _require_approver():
    roles = set(frappe.get_roles(frappe.session.user))
    if not roles.intersection({"System Manager", "Administrator", "Rental Manager", "Cortex Account Reviewer"}):
        frappe.throw(
            "Votre rôle ne permet pas de décider une approbation.",
            frappe.PermissionError,
        )


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
        rows = frappe.get_all(
            "Approval Request",
            filters=filters,
            fields=["name"],
            order_by="creation desc",
            start=(page - 1) * page_size,
            page_length=page_size,
        )
        items = [_serialize(frappe.get_doc("Approval Request", row.name)) for row in rows]
        return {
            "data": {
                "provenance": "api",
                "last_synced_at": frappe.utils.now_datetime().isoformat(),
                "items": items,
                "total_count": total,
            }
        }

    @frappe.whitelist(methods=["GET"])
    def get_approval_request(name: str):
        _require_approver()
        doc = frappe.get_doc("Approval Request", name)
        if doc.company != get_company_context():
            frappe.throw("Demande d’approbation introuvable.", frappe.PermissionError)
        return {"data": _serialize(doc)}

    @frappe.whitelist(methods=["GET"])
    def decision_options(name: str):
        """Ce que la personne connectée peut faire de cette demande (le serveur reste seul juge à la décision)."""
        from cortex_rental.services import approval_policy
        from cortex_rental.cortex_rental.doctype.approval_request.approval_request import (
            APPROVER_ROLES,
            other_approvers,
            sole_approver_may_self_approve,
        )

        doc = frappe.get_doc("Approval Request", name)
        if doc.company != get_company_context():
            frappe.throw("Demande d’approbation introuvable.", frappe.PermissionError)
        user = frappe.session.user
        pending = doc.status == "Pending"
        is_approver = bool(APPROVER_ROLES.intersection(frappe.get_roles(user)))
        mine = doc.requested_by_type == "Human" and doc.requested_by_id == user
        if not pending:
            return {"can_approve": False, "can_reject": False, "can_withdraw": False, "note": ""}
        if mine:
            sole_allowed = is_approver and sole_approver_may_self_approve(doc.company, user)
            alone = not other_approvers(doc.company, user)
            policy = approval_policy.get_policy(doc.company, user)
            if sole_allowed:
                note = "Vous êtes la seule personne autorisée de votre société : votre approbation sera notée comme une auto-approbation."
            elif alone:
                note = (
                    "Vous êtes la seule personne autorisée de votre société : personne ne peut approuver cette demande. "
                    "Ajoutez une personne autorisée dans « Équipe et rôles »"
                    + (
                        " ou lisez ce que change l'auto-approbation avant de l'activer."
                        if policy["can_manage"]
                        else "."
                    )
                )
            else:
                note = "Vous avez fait cette demande : une autre personne autorisée doit la décider."
            return {
                "can_approve": sole_allowed,
                "can_reject": False,
                "can_withdraw": True,
                "self_approval": sole_allowed,
                "can_explain_policy": bool(alone and policy["can_manage"] and not sole_allowed),
                "note": note,
            }
        return {"can_approve": is_approver, "can_reject": is_approver, "can_withdraw": False, "note": ""}

    @frappe.whitelist(methods=["GET"])
    def self_approval_policy():
        """État de la règle « le seul approbateur décide de ses propres demandes », avec ses bénéfices et ses dangers."""
        from cortex_rental.services import approval_policy

        return approval_policy.get_policy(get_company_context(), frappe.session.user)

    @frappe.whitelist(methods=["POST"])
    def set_self_approval(enabled: int = 0, acknowledged: int = 0):
        """Active ou désactive la règle (propriétaire seulement). L'activation exige d'avoir confirmé la lecture des risques."""
        from cortex_rental.services import approval_policy

        return approval_policy.set_self_approval(
            get_company_context(), frappe.session.user, bool(int(enabled)), bool(int(acknowledged))
        )

    @frappe.whitelist(methods=["POST"])
    def decide_approval(name: str, decision: str, reason: str = None):
        decision = (decision or "").lower()
        if decision != "withdraw":
            _require_approver()
        doc = frappe.get_doc("Approval Request", name)
        if doc.company != get_company_context():
            frappe.throw("Demande d’approbation introuvable.", frappe.PermissionError)
        if decision == "approve":
            doc.approve(reason=reason)
        elif decision == "withdraw":
            doc.withdraw(reason=reason)
        elif decision == "reject":
            if not reason or len(reason.strip()) < 3:
                frappe.throw(
                    "Un motif de refus d’au moins trois caractères est obligatoire.",
                    frappe.ValidationError,
                )
            doc.reject(reason=reason)
        else:
            frappe.throw("La décision doit être « approuver », « refuser » ou « retirer ».", frappe.ValidationError)
        return {
            "request_id": frappe.generate_hash(length=16),
            "entity_id": name,
            "status": "completed",
            "approval_required": False,
            "mutation_performed": True,
        }
