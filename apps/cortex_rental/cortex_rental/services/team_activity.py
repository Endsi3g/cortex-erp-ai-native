"""Activité de l'équipe : qui est en ligne et ce que chacun vient de faire (à partir du journal d'audit).

Les données sont celles de la société de la personne connectée, jamais d'une autre. « En ligne » = un battement de
cœur reçu dans les 3 dernières minutes (`presence.ping`). Les actions viennent du journal d'audit immuable : aucune
activité n'est inventée.
"""

from typing import Any, Dict, List

try:
    import frappe
    from frappe.utils import add_to_date, now_datetime
except ImportError:
    frappe = None

ONLINE_WINDOW_MINUTES = 3

# Phrases françaises des actions du journal d'audit (seulement les actions qui montrent du travail réel).
ACTION_TEXT = {
    "cortex.rental_transaction.draft_created": "a créé un devis",
    "cortex.rental_transaction.quote_updated": "a modifié un devis",
    "cortex.rental_transaction.transition_to_reservation": "a réservé du matériel",
    "cortex.rental_transaction.transition_to_contract": "a confirmé un contrat",
    "cortex.rental_transaction.transition_to_checked out": "a fait sortir du matériel",
    "cortex.rental_transaction.transition_to_returned": "a enregistré un retour",
    "cortex.rental_transaction.transition_to_closed": "a clôturé une location",
    "cortex.rental_transaction.transition_to_cancelled": "a annulé une location",
    "cortex.rental_transaction.transition_to_disputed": "a ouvert un litige",
    "cortex.check_in.completed": "a enregistré un retour",
    "cortex.approval_request.submitted": "a demandé une approbation",
    "rental.approval.approved": "a approuvé une demande",
    "rental.approval.rejected": "a refusé une demande",
    "cortex.quote.shared": "a partagé un devis avec un client",
    "cortex.quote.accepted": "a accepté le devis",
    "cortex.quote.declined": "a refusé le devis",
    "cortex.quote.changes_requested": "demande une modification du devis",
    "cortex.invoice.issued": "a émis une facture",
    "cortex.payment.recorded": "a enregistré un paiement",
    "cortex.customer.draft_created": "a ajouté un client",
    "cortex.inbound_request.processed": "a traité une demande entrante",
    "cortex.pricing_rule.created": "a créé une règle tarifaire",
    "cortex.pricing_rule.updated": "a modifié une règle tarifaire",
    "cortex.team.member_enabled": "a réactivé un membre",
    "cortex.team.member_disabled": "a désactivé un membre",
    "cortex.team.role_changed": "a changé des rôles",
    "cortex.onboarding.member_invited": "a invité un membre",
}


def action_text(action: str) -> str:
    return ACTION_TEXT.get(action or "", "")


def company_members(company: str) -> List[str]:
    return frappe.get_all(
        "User Permission", filters={"allow": "Company", "for_value": company}, pluck="user", distinct=True
    )


def publish_company_activity(company: str, payload: Dict[str, Any]) -> None:
    """Prévient en temps réel les membres de la société qu'une action vient d'avoir lieu (après validation en base)."""
    if not frappe or not company:
        return
    for user in company_members(company):
        frappe.publish_realtime("cortex_activity", payload, user=user, after_commit=True)


def team_snapshot(company: str, me: str, limit: int = 12) -> Dict[str, Any]:
    members = company_members(company)
    if me not in members:
        members.append(me)
    users = frappe.get_all(
        "User",
        filters={"name": ["in", members], "enabled": 1},
        fields=["name", "full_name", "user_image", "last_active"],
    )
    threshold = add_to_date(now_datetime(), minutes=-ONLINE_WINDOW_MINUTES)
    events = frappe.get_all(
        "Audit Event",
        filters={"company": company, "actor_type": ["in", ["Human", "Customer"]], "action": ["in", list(ACTION_TEXT)]},
        fields=["actor_id", "action", "entity_type", "entity_id", "creation"],
        order_by="creation desc",
        limit_page_length=limit * 3,
    )
    last_by_user: Dict[str, Dict[str, Any]] = {}
    for event in events:
        last_by_user.setdefault(event.actor_id, event)
    team = []
    for user in users:
        event = last_by_user.get(user.name)
        team.append(
            {
                "user": user.name,
                "full_name": user.full_name or user.name,
                "image": user.user_image or "",
                "online": bool(user.last_active and user.last_active >= threshold),
                "is_me": user.name == me,
                "last_action": action_text(event.action) if event else "",
                "last_action_at": str(event.creation) if event else "",
            }
        )
    team.sort(key=lambda m: (not m["online"], m["full_name"].lower()))
    names = {u.name: u.full_name or u.name for u in users}
    activity = [
        {
            "actor": names.get(e.actor_id, e.actor_id),
            "text": action_text(e.action),
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "at": str(e.creation),
        }
        for e in events[:limit]
    ]
    return {
        "provenance": "audit",
        "online_count": sum(1 for m in team if m["online"]),
        "team": team,
        "activity": activity,
    }
