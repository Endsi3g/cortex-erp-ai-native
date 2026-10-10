"""Catalogue d'actions de l'assistant : chaque action lit les vrais enregistrements, montre un aperçu, et écrit par la
fonction de l'écran correspondant, avec les droits de la personne (voir actions.py et ADR-011).

Règles : valider d'abord (état, droits, société), refuser clairement sinon; ne jamais deviner un identifiant; dire dans
`effects` ce que l'action fera, ne fera pas, et comment revenir en arrière.
"""

from typing import Any, Dict

try:
    import frappe
except ImportError:  # tests unitaires sans bench
    frappe = None

from cortex_rental.services.ai.actions import ActionError, ActionSpec, Prepared, href_for, register
from cortex_rental.services.ai.stats import human_dt, money

TX = "Cortex Rental Transaction"


def _need(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ActionError(f"{label} est obligatoire.")
    return text


def _transaction(args: Dict[str, Any], company: str):
    name = _need(args.get("rental") or args.get("rental_id"), "La location")
    if not frappe.db.exists(TX, {"name": name, "company": company}):
        raise ActionError("Cette location n'existe pas dans votre société.")
    doc = frappe.get_doc(TX, name)
    if not frappe.has_permission(TX, "write", doc=doc):
        raise ActionError("Votre rôle ne permet pas de modifier cette location.")
    return doc


def _rental_rows(doc) -> list:
    rows = [
        {"label": "Location", "value": doc.name},
        {"label": "Client", "value": str(doc.customer or "—")},
        {"label": "Période", "value": f"{human_dt(doc.starts_at)} → {human_dt(doc.ends_at)}"},
    ]
    if doc.get("hold_until"):
        rows.append({"label": "Retenue jusqu'au", "value": human_dt(doc.hold_until)})
    return rows


def _lines(rows) -> list:
    return [f"{r['label']} : {r.get('value', '')}" for r in rows]


# --- Libérer / renouveler la retenue d'un devis -------------------------------------------------------------------


def _prepare_release_hold(args: Dict[str, Any], company: str) -> Prepared:
    doc = _transaction(args, company)
    if doc.rental_state != "Quote":
        raise ActionError("Seul un devis retient le matériel.")
    if doc.get("hold_status") != "Active":
        raise ActionError("Ce devis ne retient aucun matériel en ce moment.")
    rows = _rental_rows(doc)
    return Prepared(
        {"rental": doc.name},
        f"Libérer la retenue de {doc.name}",
        _lines(rows),
        rows=rows,
        subtitle="Le matériel retenu redevient disponible pour les autres",
        approve_label="Libérer la retenue",
    )


def _run_release_hold(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    from cortex_rental.services import holds

    doc = _transaction(payload, company)
    holds.release(doc.name, "Libérée par une personne autorisée (proposée par l'assistant)")
    return {"id": doc.name, "label": "Ouvrir la location", "href": href_for(TX, doc.name)}


def _prepare_renew_hold(args: Dict[str, Any], company: str) -> Prepared:
    doc = _transaction(args, company)
    if doc.rental_state != "Quote":
        raise ActionError("Seul un devis retient le matériel.")
    rows = _rental_rows(doc)
    rows.append({"label": "État de la retenue", "value": str(doc.get("hold_status") or "Aucune")})
    return Prepared(
        {"rental": doc.name},
        f"Renouveler la retenue de {doc.name}",
        _lines(rows),
        rows=rows,
        subtitle="La disponibilité est revérifiée au moment d'approuver",
        approve_label="Renouveler la retenue",
    )


def _run_renew_hold(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    from cortex_rental.services import holds

    doc = _transaction(payload, company)
    result = holds.evaluate(doc)
    if result.get("status") != "Active":
        # Pas de retenue prise : on le dit, on ne présente jamais cela comme réussi.
        raise ValueError(result.get("note") or "La retenue n'a pas pu être renouvelée.")
    return {"id": doc.name, "label": "Ouvrir la location", "href": href_for(TX, doc.name)}


# --- Demander une réservation ---------------------------------------------------------------------------------------


def _prepare_reservation(args: Dict[str, Any], company: str) -> Prepared:
    from cortex_rental.services.availability import AvailabilityService

    doc = _transaction(args, company)
    if doc.rental_state != "Quote":
        raise ActionError("Seul un devis peut devenir une réservation.")
    requests = [{"item_id": r.item_code, "quantity": float(r.qty or 0)} for r in doc.items or [] if r.item_code]
    if not requests:
        raise ActionError("Ce devis n'a aucun équipement.")
    checks = AvailabilityService().check(
        company=company,
        starts_at=str(doc.starts_at),
        ends_at=str(doc.ends_at),
        item_requests=requests,
        exclude_transaction=doc.name,
    )
    short = [c for c in checks if not c["is_available"]]
    if short:
        raise ActionError(
            "Disponibilité insuffisante : "
            + "; ".join(
                f"{c['item_id']} ({c['available_quantity']:g} libre(s) sur {c['requested_quantity']:g})" for c in short
            )
        )
    rows = _rental_rows(doc)
    rows += [
        {"label": str(r.item_name or r.item_code), "detail": f"× {float(r.qty or 0):g}", "value": "Disponible"}
        for r in doc.items or []
    ]
    totals = [{"label": "Total", "value": money(doc.grand_total)}]
    return Prepared(
        {"rental": doc.name},
        f"Réserver {doc.name}",
        _lines(rows) + [f"Total : {money(doc.grand_total)}"],
        rows=rows,
        totals=totals,
        subtitle="Disponibilité vérifiée à l'instant",
        approve_label="Confirmer la réservation",
    )


def _run_reservation(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    doc = _transaction(payload, company)
    doc.transition_to("Reservation", reason="Confirmé par une personne autorisée (proposé par l'assistant)")
    return {"id": doc.name, "label": "Ouvrir la réservation", "href": href_for(TX, doc.name)}


# --- Enregistrer un paiement ------------------------------------------------------------------------------------------

METHODS = ("Card", "Cash", "Bank Transfer", "Cheque", "Other")
METHOD_LABELS = {"Card": "Carte", "Cash": "Comptant", "Bank Transfer": "Virement", "Cheque": "Chèque", "Other": "Autre"}


def _invoice(args: Dict[str, Any], company: str):
    name = _need(args.get("invoice"), "La facture")
    row = frappe.db.get_value(
        "Cortex Rental Invoice",
        {"name": name, "company": company},
        ["name", "customer", "status", "total", "balance"],
        as_dict=True,
    )
    if not row:
        raise ActionError("Cette facture n'existe pas dans votre société.")
    return row


def _prepare_payment(args: Dict[str, Any], company: str) -> Prepared:
    inv = _invoice(args, company)
    if inv.status not in ("Issued", "Partially Paid"):
        raise ActionError("Cette facture n'accepte plus de paiement (déjà payée ou annulée).")
    try:
        amount = round(float(args.get("amount")), 2)
    except (TypeError, ValueError):
        raise ActionError("Le montant du paiement est obligatoire.")
    balance = round(float(inv.balance or 0), 2)
    if amount <= 0:
        raise ActionError("Le montant doit être supérieur à zéro.")
    if amount > balance:
        raise ActionError(f"Le montant dépasse le solde de la facture ({money(balance)}).")
    method = str(args.get("method") or "Card")
    if method not in METHODS:
        raise ActionError("Mode de paiement inconnu (carte, comptant, virement, chèque ou autre).")
    reference = " ".join(str(args.get("reference") or "").split())[:140]
    rows = [
        {"label": "Facture", "value": inv.name},
        {"label": "Client", "value": str(inv.customer or "—")},
        {"label": "Mode de paiement", "value": METHOD_LABELS[method]},
        {"label": "Solde avant", "value": money(balance)},
    ]
    if reference:
        rows.append({"label": "Référence", "value": reference})
    totals = [{"label": "Paiement", "value": money(amount)}, {"label": "Solde après", "value": money(balance - amount)}]
    return Prepared(
        {"invoice": inv.name, "amount": amount, "method": method, "reference": reference},
        f"Paiement de {money(amount)} sur {inv.name}",
        _lines(rows) + [f"Paiement : {money(amount)}", f"Solde après : {money(balance - amount)}"],
        rows=rows,
        totals=totals,
        subtitle="Le solde de la facture est mis à jour",
        approve_label="Enregistrer le paiement",
    )


def _run_payment(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    from cortex_rental.services import billing

    doc = billing.record_payment(
        invoice=payload["invoice"],
        amount=payload["amount"],
        method=payload["method"],
        reference=payload.get("reference") or None,
        notes="Enregistré par une personne autorisée (proposé par l'assistant)",
    )
    return {"id": doc.name, "label": "Ouvrir la facture", "href": href_for("Cortex Rental Invoice", payload["invoice"])}


# --- Décider une demande d'approbation -----------------------------------------------------------------------------------


def _approval(args: Dict[str, Any], company: str):
    from cortex_rental.api.v1.approval_queue import _require_approver

    name = _need(args.get("approval"), "La demande d'approbation")
    try:
        _require_approver()
    except Exception as exc:
        raise ActionError(str(getattr(exc, "message", None) or exc))
    row = frappe.db.get_value(
        "Approval Request",
        {"name": name, "company": company},
        ["name", "action", "entity_type", "entity_id", "requested_by_id", "status"],
        as_dict=True,
    )
    if not row:
        raise ActionError("Cette demande d'approbation n'existe pas dans votre société.")
    return row


def _prepare_decision(args: Dict[str, Any], company: str) -> Prepared:
    row = _approval(args, company)
    if row.status != "Pending":
        raise ActionError("Cette demande a déjà été décidée.")
    decision = str(args.get("decision") or "").lower()
    if decision not in ("approve", "reject"):
        raise ActionError("La décision doit être « approuver » ou « refuser ».")
    reason = " ".join(str(args.get("decision_reason") or args.get("reason") or "").split())[:300]
    if decision == "reject" and len(reason) < 3:
        raise ActionError("Un motif de refus d'au moins trois caractères est obligatoire.")
    label = "Approuver" if decision == "approve" else "Refuser"
    rows = [
        {"label": "Demande", "value": row.name},
        {"label": "Action demandée", "value": str(row.action or "—")},
        {"label": "Concerne", "value": f"{row.entity_type} {row.entity_id}"},
        {"label": "Demandée par", "value": str(row.requested_by_id or "—")},
        {"label": "Votre décision", "value": label},
    ]
    if reason:
        rows.append({"label": "Motif", "value": reason})
    return Prepared(
        {"approval": row.name, "decision": decision, "reason": reason},
        f"{label} la demande {row.name}",
        _lines(rows),
        rows=rows,
        subtitle="Les règles d'approbation de votre société s'appliquent encore à l'exécution",
        approve_label=f"{label} la demande",
    )


def _run_decision(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    row = _approval(payload, company)
    doc = frappe.get_doc("Approval Request", row.name)
    if payload["decision"] == "approve":
        doc.approve(reason=payload.get("reason") or "Approuvé par une personne autorisée (proposé par l'assistant)")
    else:
        doc.reject(reason=payload["reason"])
    return {"id": row.name, "label": "Ouvrir la demande", "href": href_for("Approval Request", row.name)}


register(
    ActionSpec(
        "release_hold",
        "Libérer la retenue",
        TX,
        "write",
        _prepare_release_hold,
        _run_release_hold,
        effects=(
            "Le matériel retenu par ce devis redevient disponible pour d'autres.",
            "Le devis lui-même n'est ni supprimé ni annulé; rien n'est envoyé au client.",
            "Pour revenir en arrière : « Renouveler la retenue » (la disponibilité est alors revérifiée).",
        ),
    )
)
register(
    ActionSpec(
        "renew_hold",
        "Renouveler la retenue",
        TX,
        "write",
        _prepare_renew_hold,
        _run_renew_hold,
        effects=(
            "Reprend la retenue du matériel pour la durée prévue par vos règles, si le matériel est encore libre.",
            "Si le matériel n'est plus disponible, rien n'est retenu et le message le dit.",
            "Pour revenir en arrière : « Libérer la retenue ».",
        ),
    )
)
register(
    ActionSpec(
        "request_reservation",
        "Confirmer la réservation",
        TX,
        "write",
        _prepare_reservation,
        _run_reservation,
        effects=(
            "Le devis devient une réservation : le matériel est réservé pour la période.",
            "Aucun contrat n'est signé ni approuvé par cette action; un contrat demande l'approbation d'une personne.",
            "Pour revenir en arrière : annuler la réservation avec un motif, depuis la location.",
        ),
    )
)
register(
    ActionSpec(
        "record_payment",
        "Enregistrer un paiement",
        "Cortex Rental Payment",
        "create",
        _prepare_payment,
        _run_payment,
        effects=(
            "Enregistre le paiement, met à jour le solde de la facture et génère les écritures comptables.",
            "Aucun argent n'est prélevé : on note un paiement déjà reçu.",
            "Un paiement ne se supprime pas (journal comptable immuable). Pour corriger : un remboursement qui l'annule, la trace reste.",
        ),
    )
)
register(
    ActionSpec(
        "decide_approval",
        "Décider une approbation",
        "Approval Request",
        "read",
        _prepare_decision,
        _run_decision,
        effects=(
            "Approuve ou refuse la demande au nom de la personne connectée, selon son rôle d'approbateur.",
            "Les règles de votre société (par exemple, personne ne décide de sa propre demande) s'appliquent à l'exécution.",
            "Une décision ne se défait pas : une nouvelle demande est nécessaire.",
        ),
    )
)
