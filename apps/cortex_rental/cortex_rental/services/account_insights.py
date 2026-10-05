"""Mon compte, en profondeur : statistiques personnelles, historique complet, approbations, connexions, droits.

Tout est lu dans les dossiers réels (journal d'audit immuable, demandes d'approbation, retours, paiements, usage de
l'IA) pour la personne connectée et sa société seulement. Aucun chiffre n'est estimé : un compteur à zéro veut dire
« aucune action dans la période ».
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional

try:
    import frappe
    from frappe.utils import add_days, cint, flt, get_datetime, now_datetime, today
except ImportError:
    frappe = None

PERIODS = {"7": 7, "30": 30, "90": 90, "365": 365, "all": None}

# Phrases de l'historique personnel (« Devis créé ») : on parle de l'action, pas de la personne.
PERSONAL_TEXT = {
    "cortex.rental_transaction.draft_created": ("Devis créé", "location"),
    "cortex.rental_transaction.quote_updated": ("Devis modifié", "location"),
    "cortex.rental_transaction.transition_to_reservation": ("Matériel réservé", "location"),
    "cortex.rental_transaction.transition_to_contract": ("Contrat confirmé", "location"),
    "cortex.rental_transaction.transition_to_checked out": ("Matériel sorti", "location"),
    "cortex.rental_transaction.transition_to_returned": ("Retour enregistré", "location"),
    "cortex.rental_transaction.transition_to_closed": ("Location clôturée", "location"),
    "cortex.rental_transaction.transition_to_cancelled": ("Location annulée", "location"),
    "cortex.rental_transaction.transition_to_disputed": ("Litige ouvert", "location"),
    "cortex.check_in.completed": ("Retour de matériel complété", "location"),
    "cortex.approval_request.submitted": ("Approbation demandée", "approbation"),
    "rental.approval.approved": ("Demande approuvée", "approbation"),
    "rental.approval.rejected": ("Demande refusée", "approbation"),
    "rental.approval.withdrawn": ("Demande retirée", "approbation"),
    "cortex.quote.shared": ("Devis partagé avec le client", "client"),
    "cortex.quote.share_revoked": ("Lien de devis révoqué", "client"),
    "cortex.customer.draft_created": ("Client ajouté", "client"),
    "cortex.inbound_request.processed": ("Demande entrante traitée", "client"),
    "cortex.invoice.issued": ("Facture émise", "finance"),
    "cortex.payment.recorded": ("Paiement enregistré", "finance"),
    "cortex.pricing_rule.created": ("Règle tarifaire créée", "administration"),
    "cortex.pricing_rule.updated": ("Règle tarifaire modifiée", "administration"),
    "cortex.pricing_rule.deactivated": ("Règle tarifaire désactivée", "administration"),
    "cortex.team.member_enabled": ("Membre réactivé", "administration"),
    "cortex.team.member_disabled": ("Membre désactivé", "administration"),
    "cortex.team.role_changed": ("Rôles modifiés", "administration"),
    "cortex.onboarding.member_invited": ("Membre invité", "administration"),
    "cortex.account.session_revoked": ("Appareil déconnecté", "securite"),
    "cortex.account.sessions_revoked": ("Appareils déconnectés", "securite"),
}
CATEGORIES = {
    "location": "Locations",
    "approbation": "Approbations",
    "client": "Clients et devis",
    "finance": "Facturation et paiements",
    "administration": "Administration",
    "securite": "Sécurité",
}


def _since(period: str) -> Optional[Any]:
    days = PERIODS.get(str(period), 30)
    return add_days(now_datetime(), -days) if days else None


def _humanize(action: str) -> str:
    tail = (action or "").rsplit(".", 1)[-1].replace("_", " ").strip()
    return tail[:1].upper() + tail[1:] if tail else "Action"


def action_info(action: str) -> Dict[str, str]:
    text, category = PERSONAL_TEXT.get(action or "", (_humanize(action), "autre"))
    return {"text": text, "category": category}


def _audit_counts(company: str, user: str, since) -> Counter:
    filters: Dict[str, Any] = {"company": company, "actor_id": user, "actor_type": "Human"}
    if since:
        filters["creation"] = [">=", since]
    rows = frappe.get_all("Audit Event", filters=filters, fields=["action", "count(name) as n"], group_by="action")
    return Counter({r.action: int(r.n) for r in rows})


def stats(user: str, company: str, period: str = "30") -> Dict[str, Any]:
    since = _since(period)
    counts = _audit_counts(company, user, since)
    c = lambda *a: sum(counts.get(x, 0) for x in a)  # noqa: E731
    base = "cortex.rental_transaction.transition_to_"

    result: Dict[str, Any] = {
        "period": str(period) if str(period) in PERIODS else "30",
        "since": str(since)[:10] if since else None,
        "actions_total": sum(counts.values()),
        "work": {
            "quotes_created": c("cortex.rental_transaction.draft_created"),
            "reservations": c(base + "reservation"),
            "contracts": c(base + "contract"),
            "checkouts": c(base + "checked out"),
            "returns": c("cortex.check_in.completed"),
            "closed": c(base + "closed"),
            "cancelled": c(base + "cancelled"),
            "disputes": c(base + "disputed"),
            "quotes_shared": c("cortex.quote.shared"),
            "customers_added": c("cortex.customer.draft_created"),
            "invoices_issued": c("cortex.invoice.issued"),
            "payments_recorded": c("cortex.payment.recorded"),
        },
    }
    result["approvals"] = approval_counts(user, company, since)
    result["equipment"] = equipment_flow(user, company, since)
    result["money"] = money(user, company, since)
    result["conversion"] = conversion(user, company, since)
    result["ai"] = ai_use(user, company, since)
    result["logins"] = login_count(user, since)
    result["daily"] = daily_series(user, company, 30 if not since else min(PERIODS.get(str(period)) or 30, 30))
    return result


def approval_counts(user: str, company: str, since) -> Dict[str, int]:
    def count(extra: Dict[str, Any], stamp: str = "creation") -> int:
        filters = {"company": company, **extra}
        if since:
            filters[stamp] = [">=", since]
        return frappe.db.count("Approval Request", filters=filters)

    approved = count({"decided_by": user, "status": "Approved"}, "decided_at")
    rejected = frappe.db.count(
        "Approval Request",
        filters={
            "company": company,
            "decided_by": user,
            "status": "Rejected",
            "requested_by_id": ["!=", user],
            **({"decided_at": [">=", since]} if since else {}),
        },
    )
    withdrawn = frappe.db.count(
        "Approval Request",
        filters={
            "company": company,
            "decided_by": user,
            "requested_by_id": user,
            "status": "Rejected",
            **({"decided_at": [">=", since]} if since else {}),
        },
    )
    return {
        "requested": count({"requested_by_id": user}),
        "approved_by_me": approved,
        "rejected_by_me": rejected,
        "withdrawn": withdrawn,
        "my_requests_pending": frappe.db.count(
            "Approval Request", {"company": company, "requested_by_id": user, "status": "Pending"}
        ),
        "mine_to_decide": frappe.db.count(
            "Approval Request", {"company": company, "status": "Pending", "requested_by_id": ["!=", user]}
        ),
    }


def equipment_flow(user: str, company: str, since) -> Dict[str, Any]:
    """Matériel sorti et retourné par la personne : unités, locations et équipements les plus sortis."""
    filters: Dict[str, Any] = {
        "company": company,
        "actor_id": user,
        "action": "cortex.rental_transaction.transition_to_checked out",
    }
    if since:
        filters["creation"] = [">=", since]
    txs = list(dict.fromkeys(frappe.get_all("Audit Event", filters=filters, pluck="entity_id", limit_page_length=5000)))
    units_out, by_item = 0.0, Counter()
    if txs:
        rows = frappe.get_all(
            "Cortex Rental Transaction Item",
            filters={"parent": ["in", txs]},
            fields=["item_code", "item_name", "qty"],
            limit_page_length=0,
        )
        names: Dict[str, str] = {}
        for row in rows:
            units_out += flt(row.qty)
            by_item[row.item_code] += flt(row.qty)
            names[row.item_code] = row.item_name or row.item_code
        top = [{"item": names[code], "units": round(qty, 1)} for code, qty in by_item.most_common(5)]
    else:
        top = []
    check_filters: Dict[str, Any] = {"company": company, "checked_in_by": user, "status": "Completed"}
    if since:
        check_filters["checked_in_at"] = [">=", since]
    check_ins = frappe.get_all("Cortex Check-In", filters=check_filters, pluck="name", limit_page_length=5000)
    units_back, damaged, missing = 0.0, 0, 0
    if check_ins:
        for row in frappe.get_all(
            "Cortex Check-In Item",
            filters={"parent": ["in", check_ins]},
            fields=["returned_qty", "condition"],
            limit_page_length=0,
        ):
            units_back += flt(row.returned_qty)
            damaged += 1 if row.condition == "Damaged" else 0
            missing += 1 if row.condition == "Missing" else 0
    return {
        "rentals_checked_out": len(txs),
        "units_checked_out": round(units_out, 1),
        "units_returned": round(units_back, 1),
        "returns_with_damage": damaged,
        "items_missing": missing,
        "top_items": top,
    }


def money(user: str, company: str, since) -> Dict[str, float]:
    filters: Dict[str, Any] = {"company": company, "owner": user}
    if since:
        filters["creation"] = [">=", since]
    quotes = frappe.get_all("Cortex Rental Transaction", filters=filters, fields=["sum(grand_total) as total"])[0]
    pay_filters: Dict[str, Any] = {"company": company, "owner": user}
    if since:
        pay_filters["creation"] = [">=", since]
    pays = frappe.get_all("Cortex Rental Payment", filters=pay_filters, fields=["sum(signed_amount) as total"])[0]
    return {"quoted_value": round(flt(quotes.total), 2), "payments_recorded": round(flt(pays.total), 2)}


def conversion(user: str, company: str, since) -> Dict[str, Any]:
    """Parmi les devis créés par la personne, la part qui est devenue une réservation ou plus."""
    filters: Dict[str, Any] = {"company": company, "owner": user}
    if since:
        filters["creation"] = [">=", since]
    rows = frappe.get_all("Cortex Rental Transaction", filters=filters, fields=["rental_state"], limit_page_length=0)
    total = len(rows)
    won = sum(
        1
        for r in rows
        if r.rental_state in ("Reservation", "Contract", "Checked Out", "Partially Returned", "Returned", "Closed")
    )
    return {"created": total, "advanced": won, "rate": round(won / total * 100, 1) if total else None}


def ai_use(user: str, company: str, since) -> Dict[str, Any]:
    if not frappe.has_permission("Cortex AI Usage", "read"):
        return {"visible": False}
    filters: Dict[str, Any] = {"company": company, "user": user}
    if since:
        filters["creation"] = [">=", since]
    row = frappe.get_all(
        "Cortex AI Usage",
        filters=filters,
        fields=["count(name) as calls", "sum(input_tokens) as tin", "sum(output_tokens) as tout", "sum(cost) as cost"],
    )[0]
    return {
        "visible": True,
        "calls": int(row.calls or 0),
        "tokens": int(flt(row.tin) + flt(row.tout)),
        "cost": round(flt(row.cost), 2),
    }


def login_count(user: str, since) -> int:
    filters: Dict[str, Any] = {"user": user, "operation": "Login", "status": "Success"}
    if since:
        filters["creation"] = [">=", since]
    return frappe.db.count("Activity Log", filters=filters)


def daily_series(user: str, company: str, days: int) -> List[Dict[str, Any]]:
    start = add_days(today(), -(days - 1))
    rows = frappe.get_all(
        "Audit Event",
        filters={"company": company, "actor_id": user, "actor_type": "Human", "creation": [">=", start]},
        pluck="creation",
        limit_page_length=20000,
    )
    per_day = Counter(str(get_datetime(r))[:10] for r in rows)
    return [{"date": str(add_days(start, i)), "count": per_day.get(str(add_days(start, i)), 0)} for i in range(days)]


# ---------------------------------------------------------------------------------------------- historique
def history(
    user: str, company: str, category: str = "", period: str = "90", limit: int = 30, offset: int = 0
) -> Dict[str, Any]:
    actions = [a for a, (_t, cat) in PERSONAL_TEXT.items() if not category or cat == category]
    filters: Dict[str, Any] = {"company": company, "actor_id": user, "actor_type": "Human"}
    if category:
        filters["action"] = ["in", actions or ["-"]]
    since = _since(period)
    if since:
        filters["creation"] = [">=", since]
    limit = max(1, min(cint(limit) or 30, 100))
    offset = max(0, cint(offset))
    total = frappe.db.count("Audit Event", filters=filters)
    rows = frappe.get_all(
        "Audit Event",
        filters=filters,
        fields=["action", "entity_type", "entity_id", "creation", "after_state"],
        order_by="creation desc",
        start=offset,
        page_length=limit,
    )
    items = []
    for row in rows:
        info = action_info(row.action)
        detail = ""
        if row.after_state:
            try:
                state = frappe.parse_json(row.after_state)
                if isinstance(state, dict):
                    detail = str(state.get("decision_reason") or state.get("reason") or "")[:160]
            except Exception:  # noqa: BLE001
                detail = ""
        items.append(
            {
                "text": info["text"],
                "category": info["category"],
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "at": str(row.creation)[:16],
                "detail": detail,
            }
        )
    return {"items": items, "total": total, "has_more": offset + len(items) < total, "categories": CATEGORIES}


# ---------------------------------------------------------------------------------------------- approbations
def my_approvals(user: str, company: str, limit: int = 40) -> Dict[str, Any]:
    from cortex_rental.labels import approval_label

    fields = [
        "name",
        "action",
        "status",
        "entity_type",
        "entity_id",
        "requested_by_id",
        "decided_by",
        "decided_at",
        "decision_reason",
        "creation",
    ]

    def row(r) -> Dict[str, Any]:
        verb = (r.action or "").rsplit(".", 1)[-1]
        names = {
            "transition_to_contract": "Confirmer un contrat",
            "transition_to_reservation": "Confirmer une réservation",
            "transition_to_checked out": "Faire sortir le matériel",
            "transition_to_closed": "Clôturer la location",
            "transition_to_cancelled": "Annuler la location",
        }
        return {
            "id": r.name,
            "what": names.get(verb, _humanize(r.action)),
            "status": r.status,
            "status_label": approval_label(r.status),
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "requested_by": r.requested_by_id,
            "decided_by": r.decided_by or "",
            "decided_at": str(r.decided_at)[:16] if r.decided_at else "",
            "reason": r.decision_reason or "",
            "created": str(r.creation)[:16],
            "self_decided": bool(r.decided_by and r.decided_by == r.requested_by_id and r.status == "Approved"),
        }

    limit = max(1, min(cint(limit) or 40, 100))
    asked = frappe.get_all(
        "Approval Request",
        filters={"company": company, "requested_by_id": user},
        fields=fields,
        order_by="creation desc",
        page_length=limit,
    )
    decided = frappe.get_all(
        "Approval Request",
        filters={"company": company, "decided_by": user, "requested_by_id": ["!=", user]},
        fields=fields,
        order_by="decided_at desc",
        page_length=limit,
    )
    return {"requested": [row(r) for r in asked], "decided": [row(r) for r in decided]}


# ---------------------------------------------------------------------------------------------- connexions
def login_history(user: str, limit: int = 25) -> Dict[str, Any]:
    rows = frappe.get_all(
        "Activity Log",
        filters={"user": user, "operation": "Login"},
        fields=["status", "ip_address", "creation", "subject"],
        order_by="creation desc",
        page_length=max(1, min(cint(limit) or 25, 100)),
    )
    return {
        "logins": [
            {
                "ok": r.status == "Success",
                "ip": r.ip_address or "",
                "at": str(r.creation)[:16],
                "subject": r.subject or "",
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------------------------- notifications
def inbox(user: str, limit: int = 30) -> Dict[str, Any]:
    rows = frappe.get_all(
        "Notification Log",
        filters={"for_user": user},
        fields=["name", "subject", "type", "read", "document_type", "document_name", "creation"],
        order_by="creation desc",
        page_length=max(1, min(cint(limit) or 30, 100)),
    )
    unread = frappe.db.count("Notification Log", {"for_user": user, "read": 0})
    return {
        "unread": unread,
        "items": [
            {
                "id": r.name,
                "text": re.sub(r"<[^>]+>", "", r.subject or "")[:240],
                "read": bool(r.read),
                "entity_type": r.document_type or "",
                "entity_id": r.document_name or "",
                "at": str(r.creation)[:16],
            }
            for r in rows
        ],
    }


def mark_all_read(user: str) -> int:
    count = frappe.db.count("Notification Log", {"for_user": user, "read": 0})
    frappe.db.sql("UPDATE `tabNotification Log` SET `read`=1 WHERE for_user=%s AND `read`=0", (user,))
    frappe.cache.hdel("notification_count", user)
    return count


PREFERENCE_FIELDS = {
    "notify_hold_expiring": "Une retenue de devis expire bientôt",
    "notify_late_returns": "Un retour est en retard",
    "notify_quote_unanswered": "Un devis partagé reste sans réponse",
    "notify_unpaid_invoices": "Une facture est échue",
    "notify_quote_response": "Un client répond à un devis",
}


def preferences(user: str) -> Dict[str, Any]:
    values = {k: 1 for k in PREFERENCE_FIELDS}
    if frappe.db.exists("Cortex User Preference", user):
        row = frappe.db.get_value("Cortex User Preference", user, list(PREFERENCE_FIELDS), as_dict=True) or {}
        values.update({k: cint(row.get(k)) for k in PREFERENCE_FIELDS if row.get(k) is not None})
    return {"labels": PREFERENCE_FIELDS, "values": values}


def wants(user: str, field: str) -> bool:
    """La personne veut-elle cette alerte ? Oui par défaut (aucune préférence enregistrée)."""
    if field not in PREFERENCE_FIELDS:
        return True
    value = (
        frappe.db.get_value("Cortex User Preference", user, field)
        if frappe.db.exists("Cortex User Preference", user)
        else None
    )
    return True if value is None else bool(cint(value))


def update_preferences(user: str, values: Dict[str, Any]) -> Dict[str, Any]:
    clean = {k: 1 if cint(values.get(k)) else 0 for k in PREFERENCE_FIELDS if k in (values or {})}
    if not clean:
        frappe.throw("Aucun réglage à enregistrer.", frappe.ValidationError)
    if frappe.db.exists("Cortex User Preference", user):
        frappe.db.set_value("Cortex User Preference", user, clean)
    else:
        frappe.get_doc({"doctype": "Cortex User Preference", "user": user, **clean}).insert(ignore_permissions=True)
    return preferences(user)


# ---------------------------------------------------------------------------------------------- société et droits
RIGHTS_AREAS = [
    ("Locations et devis", "Cortex Rental Transaction"),
    ("Approbations", "Approval Request"),
    ("Catalogue d'équipements", "Cortex Rental Item Profile"),
    ("Clients", "Customer"),
    ("Factures", "Cortex Rental Invoice"),
    ("Paiements", "Cortex Rental Payment"),
    ("Écritures comptables", "Cortex Journal Entry"),
    ("Retours de matériel", "Cortex Check-In"),
    ("Règles tarifaires", "Rental Pricing Rule"),
    ("Journal d'audit", "Audit Event"),
    ("Consignation", "Consignment Payout"),
    ("Usage de l'IA", "Cortex AI Usage"),
]
ROLE_HELP = {
    "Rental Manager": "Gère les locations, la disponibilité et les approbations.",
    "Rental Operator": "Fait les sorties et les retours de matériel.",
    "Cortex Operations Manager": "Supervise les opérations : locations, sorties et retours.",
    "Cortex Counter Staff": "Travaille au comptoir : devis, sorties et retours.",
    "Cortex Inventory Manager": "Gère le catalogue, les numéros de série et l'état du parc.",
    "Cortex Finance Manager": "Gère la facturation, les paiements et les états financiers.",
    "Cortex Account Reviewer": "Peut approuver ou refuser des demandes.",
    "Cortex Consignment Manager": "Gère les propriétaires en consignation et leurs versements.",
    "Cortex System Manager": "Propriétaire : gère l'équipe, les règles et tous les réglages.",
    "Auditor": "Consulte l'information et le journal d'audit, sans rien modifier.",
}


def rights(user: str) -> List[Dict[str, Any]]:
    result = []
    for label, doctype in RIGHTS_AREAS:
        if not frappe.db.exists("DocType", doctype):
            continue
        can = {p: bool(frappe.has_permission(doctype, p, user=user)) for p in ("read", "create", "write")}
        result.append({"area": label, **can})
    return result


def team_roster(company: str, me: str, show_emails: bool) -> List[Dict[str, Any]]:
    from cortex_rental.services import team_activity

    members = team_activity.company_members(company)
    if me not in members:
        members.append(me)
    users = frappe.get_all(
        "User",
        filters={"name": ["in", members], "enabled": 1},
        fields=["name", "full_name", "last_login", "last_active"],
        order_by="full_name asc",
    )
    out = []
    for u in users:
        roles = sorted(r for r in frappe.get_roles(u.name) if r in ROLE_HELP)
        out.append(
            {
                "name": u.full_name or u.name,
                "email": u.name if show_emails or u.name == me else "",
                "you": u.name == me,
                "roles": roles,
                "last_active": str(u.last_active or u.last_login or "")[:16],
            }
        )
    return out
