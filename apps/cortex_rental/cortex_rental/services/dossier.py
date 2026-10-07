"""Dossier d'une fiche : tout ce qui y est relié (client, factures, paiements, approbations, retenue, partage, retours)
et son historique (qui a fait quoi, qui a demandé, qui a confirmé), pour que chaque écran mène aux autres.

Lecture seule, limitée à la société de la personne ; chaque bloc n'apparaît que si elle a le droit de lire le type de
dossier concerné. Rien n'est calculé à partir d'hypothèses : tout vient des dossiers réels et du journal d'audit.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
    from frappe.utils import flt
except ImportError:
    frappe = None

TRANSACTION = "Cortex Rental Transaction"
INVOICE = "Cortex Rental Invoice"
PAYMENT = "Cortex Rental Payment"
SUPPORTED = (TRANSACTION, INVOICE, PAYMENT)


def _can(doctype: str) -> bool:
    return bool(frappe.has_permission(doctype, "read"))


def _names(users: List[str]) -> Dict[str, str]:
    users = [u for u in set(users) if u]
    if not users:
        return {}
    return {
        u.name: u.full_name or u.name
        for u in frappe.get_all("User", filters={"name": ["in", users]}, fields=["name", "full_name"])
    }


def _customer(name: str) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    row = frappe.db.get_value("Customer", name, ["name", "customer_name"], as_dict=True)
    return {"id": row.name, "name": row.customer_name or row.name} if row else None


def _invoices(transaction: str) -> List[Dict[str, Any]]:
    if not (transaction and _can(INVOICE)):
        return []
    rows = frappe.get_all(
        INVOICE,
        filters={"rental_transaction": transaction, "status": ["!=", "Cancelled"]},
        fields=["name", "invoice_type", "status", "total", "balance"],
        order_by="creation asc",
    )
    return [
        {
            "id": r.name,
            "type": r.invoice_type,
            "status": r.status,
            "total": flt(r.total, 2),
            "balance": flt(r.balance, 2),
        }
        for r in rows
    ]


def _approvals(transaction: str) -> List[Dict[str, Any]]:
    if not (transaction and _can("Approval Request")):
        return []
    rows = frappe.get_all(
        "Approval Request",
        filters={"entity_type": TRANSACTION, "entity_id": transaction},
        fields=["name", "status", "requested_by_id", "decided_by", "decided_at", "creation"],
        order_by="creation desc",
        limit_page_length=5,
    )
    names = _names([r.requested_by_id for r in rows] + [r.decided_by for r in rows])
    return [
        {
            "id": r.name,
            "status": r.status,
            "requested_by": names.get(r.requested_by_id, r.requested_by_id or ""),
            "decided_by": names.get(r.decided_by, r.decided_by or ""),
        }
        for r in rows
    ]


def _timeline(entity_type: str, entity_id: str, company: str, limit: int = 30) -> List[Dict[str, Any]]:
    from cortex_rental.services import account_insights

    if not _can("Audit Event"):
        return []
    rows = frappe.get_all(
        "Audit Event",
        filters={
            "company": company,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_type": ["in", ["Human", "Customer"]],
        },
        fields=["action", "actor_id", "creation", "after_state"],
        order_by="creation desc",
        limit_page_length=limit,
    )
    names = _names([r.actor_id for r in rows])
    approvals = {a["id"]: a for a in _approvals(entity_id)} if entity_type == TRANSACTION else {}
    latest = next(iter(approvals.values()), None)
    items = []
    for r in rows:
        info = account_insights.action_info(r.action)
        detail = ""
        if r.after_state:
            try:
                state = frappe.parse_json(r.after_state)
                if isinstance(state, dict):
                    detail = account_insights._detail_fr(
                        str(state.get("decision_reason") or state.get("reason") or "")[:160]
                    )
            except Exception:  # noqa: BLE001
                detail = ""
        confirmed = info["category"] == "approbation" or r.action.endswith("transition_to_contract")
        items.append(
            {
                "text": info["text"],
                "category": info["category"],
                "actor": names.get(r.actor_id, r.actor_id),
                "at": str(r.creation)[:16],
                "detail": detail,
                "requested_by": latest["requested_by"] if confirmed and latest else "",
                "confirmed_by": latest["decided_by"] if confirmed and latest else "",
            }
        )
    return items


def get(doctype: str, name: str) -> Dict[str, Any]:
    from cortex_rental.permissions.agent_scopes import get_company_context

    if doctype not in SUPPORTED:
        frappe.throw("Ce type de dossier n'a pas de vue reliée.", frappe.ValidationError)
    company = get_company_context()
    doc = frappe.get_doc(doctype, name)
    if doc.company != company or not frappe.has_permission(doctype, "read", doc):
        frappe.throw("Dossier introuvable.", frappe.PermissionError)

    result: Dict[str, Any] = {"doctype": doctype, "name": name}
    if doctype == TRANSACTION:
        result.update(
            customer=_customer(doc.customer),
            invoices=_invoices(name),
            approvals=_approvals(name),
            hold={"status": doc.get("hold_status") or "", "until": str(doc.get("hold_until") or "")[:16]}
            if doc.rental_state == "Quote"
            else None,
            check_ins=[
                r.name
                for r in frappe.get_all(
                    "Cortex Check-In", filters={"transaction": name}, fields=["name"], limit_page_length=5
                )
            ]
            if _can("Cortex Check-In")
            else [],
            shares=frappe.db.count("Cortex Quote Share", {"rental_transaction": name})
            if _can("Cortex Quote Share")
            else 0,
            created_by=_names([doc.owner]).get(doc.owner, doc.owner),
        )
    elif doctype == INVOICE:
        result.update(
            customer=_customer(doc.customer),
            transaction=doc.rental_transaction,
            payments=[
                {"id": p.name, "amount": flt(p.signed_amount, 2), "paid_on": str(p.paid_on), "method": p.method}
                for p in frappe.get_all(
                    PAYMENT,
                    filters={"invoice": name},
                    fields=["name", "signed_amount", "paid_on", "method"],
                    order_by="paid_on asc",
                )
            ]
            if _can(PAYMENT)
            else [],
            journal=frappe.get_all(
                "Cortex Journal Entry", filters={"source_doctype": INVOICE, "source_name": name}, pluck="name"
            )
            if _can("Cortex Journal Entry")
            else [],
            siblings=_invoices(doc.rental_transaction),
        )
    else:
        result.update(
            customer=_customer(doc.customer),
            invoice=doc.invoice,
            transaction=doc.rental_transaction,
            journal=frappe.get_all(
                "Cortex Journal Entry", filters={"source_doctype": PAYMENT, "source_name": name}, pluck="name"
            )
            if _can("Cortex Journal Entry")
            else [],
        )
    result["timeline"] = _timeline(doctype, name, company)
    if doctype != TRANSACTION and getattr(doc, "rental_transaction", None):
        result["transaction_timeline"] = _timeline(TRANSACTION, doc.rental_transaction, company, 10)
    return result
