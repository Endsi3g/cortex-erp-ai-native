"""Actions que l'assistant PROPOSE et que la personne APPROUVE : proposer → aperçu → décision humaine → exécution.

Règles (ADR-011) :
- le modèle ne fait jamais l'écriture : il appelle un outil « proposer » qui valide, calcule l'aperçu avec les mêmes
  services que l'écran (prix du serveur, droits, société) et garde la proposition dans `Cortex AI Action`;
- seule la personne qui a posé la question peut approuver ou refuser, depuis la conversation; l'exécution se fait alors
  avec SES droits (jamais un compte de service) et passe par la même fonction que l'écran correspondant;
- avant d'exécuter, la proposition est revalidée : si l'aperçu a changé (prix, client, disponibilité), elle est périmée
  et rien n'est écrit;
- une proposition vit 24 h, ne s'exécute qu'une fois (verrou sur la ligne) et chaque issue est au journal d'audit;
- une action absente de `ACTIONS` n'existe pas : le modèle ne peut pas en inventer.
"""

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Dict, List, Optional

try:
    import frappe
except ImportError:  # tests unitaires sans bench
    frappe = None

DOCTYPE = "Cortex AI Action"
LIFETIME_HOURS = 24
MAX_OPEN_PER_USER = 20

PROPOSED, EXECUTED, REJECTED, FAILED, EXPIRED = "Proposed", "Executed", "Rejected", "Failed", "Expired"
SAVEPOINT = "cortex_ai_action"


class ActionError(Exception):
    """Refus clair, en français, montré tel quel à la personne."""


@dataclass
class Prepared:
    """Ce qu'une action valide : les données propres, un résumé et les lignes de l'aperçu (ce que la personne approuve)."""

    payload: Dict[str, Any]
    summary: str
    lines: List[str]


@dataclass
class ActionSpec:
    name: str
    label: str  # « Créer un client »
    doctype: str  # droit vérifié avant même de proposer
    ptype: str
    prepare: Callable[[Dict[str, Any], str], Prepared]
    run: Callable[[Dict[str, Any], str], Dict[str, Any]]


ACTIONS: Dict[str, ActionSpec] = {}


def register(spec: ActionSpec) -> ActionSpec:
    ACTIONS[spec.name] = spec
    return spec


# --- Pur ---------------------------------------------------------------------------------------------------------


def preview_signature(prepared_lines: List[str]) -> str:
    """Pur : empreinte de l'aperçu montré; si elle change entre la proposition et l'approbation, la proposition est périmée."""
    import hashlib

    return hashlib.sha256("\n".join(prepared_lines).encode("utf-8")).hexdigest()[:24]


def is_expired(expires_at: Any, now: Any) -> bool:
    """Pur : vrai quand la date d'expiration est passée (une date absente compte pour périmée, jamais pour éternelle)."""
    return expires_at is None or now > expires_at


def block_for(record: Dict[str, Any]) -> Dict[str, Any]:
    """Pur : le bloc de conversation qui présente la proposition (réutilise le bloc « proposal » des cartes existantes)."""
    return {
        "type": "proposal",
        "title": record["label"],
        "summary": record["summary"],
        "impact": list(record["lines"]) + ["Rien n'est fait tant que vous n'approuvez pas."],
        "action": "decide_ai_action",
        "draft_id": record["name"],
        "requires_approval": True,
    }


# --- Actions (chaque écriture passe par la fonction de l'écran correspondant) ----------------------------------------


def _prepare_customer(args: Dict[str, Any], company: str) -> Prepared:
    from cortex_rental.api.v1.customers import clean_customer_name

    try:
        name = clean_customer_name(args.get("customer_name"))
    except ValueError as exc:
        raise ActionError(str(exc))
    if frappe.db.exists("Customer", {"cortex_company": company, "customer_name": name}):
        raise ActionError(f"Un client « {name} » existe déjà.")
    return Prepared({"customer_name": name}, f"Nouveau client : {name}", [f"Client à créer : {name}"])


def _run_customer(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    from cortex_rental.api.v1.customers import insert_customer

    doc = insert_customer(company, payload["customer_name"])
    return {"id": doc.name, "label": "Ouvrir la fiche du client", "route": ["Form", "Customer", doc.name]}


def _prepare_quote(args: Dict[str, Any], company: str) -> Prepared:
    from cortex_rental.api.v1.rentals import _customer_in_company, _pricing
    from cortex_rental.services import billing

    customer = str(args.get("customer") or args.get("customer_id") or "").strip()
    if not customer:
        raise ActionError("Le client est obligatoire (utilisez la recherche de clients).")
    items = args.get("items")
    if not isinstance(items, list) or not items:
        raise ActionError("Ajoutez au moins un équipement au devis.")
    clean_items = [{"item_code": str(i.get("item_code") or ""), "quantity": i.get("quantity")} for i in items[:200]]
    try:
        _customer_in_company(customer, company)
        priced = _pricing(
            {"starts_at": args.get("starts_at"), "ends_at": args.get("ends_at"), "items": clean_items}, company
        )
    except Exception as exc:  # droits, client d'une autre société, équipement inconnu, dates invalides
        raise ActionError(str(getattr(exc, "message", None) or exc)[:300])
    tps, tvq = billing.compute_taxes(priced["subtotal"], billing.get_settings(company))
    lines = [f"{l['item_name']} × {l['quantity']:g} — {l['line_subtotal']:.2f} $" for l in priced["lines"]]
    lines.append(f"Sous-total {priced['subtotal']:.2f} $ · TPS {tps:.2f} $ · TVQ {tvq:.2f} $")
    payload = {
        "customer_id": customer,
        "starts_at": str(args.get("starts_at")),
        "ends_at": str(args.get("ends_at")),
        "items": [{"item_code": l["item_code"], "quantity": l["quantity"]} for l in priced["lines"]],
        "notes": "Proposé par l'assistant, approuvé par une personne.",
    }
    period = f"{payload['starts_at'][:16]} → {payload['ends_at'][:16]}"
    return Prepared(payload, f"Devis pour {customer} · {period}", lines)


def _run_quote(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    from cortex_rental.api.v1.rentals import _pricing, insert_quote

    priced = _pricing(payload, company)  # les prix sont recalculés par le serveur au moment d'écrire
    name = insert_quote(company, payload, priced)
    return {"id": name, "label": "Ouvrir le devis", "route": ["Form", "Cortex Rental Transaction", name]}


register(ActionSpec("create_customer", "Créer un client", "Customer", "create", _prepare_customer, _run_customer))
register(
    ActionSpec("create_quote", "Créer le devis", "Cortex Rental Transaction", "create", _prepare_quote, _run_quote)
)


# --- Cycle de vie ------------------------------------------------------------------------------------------------


def _now():
    return frappe.utils.now_datetime()


def _audit(company: str, action: str, name: str, after: Dict[str, Any]) -> None:
    try:
        from cortex_rental.services.audit import AuditService

        AuditService.record_mutation(
            company=company, action=action, entity_type=DOCTYPE, entity_id=name, after_state=after
        )
    except Exception:
        # Le journal ne doit pas défaire une décision déjà prise; l'enregistrement de l'action reste la preuve.
        frappe.log_error(title="Cortex AI action audit failed")


def propose(action_type: str, args: Dict[str, Any], company: str, user: str, session: str = "") -> Dict[str, Any]:
    """Valide et garde une proposition. Ne crée rien d'autre que la proposition elle-même."""
    spec = ACTIONS.get(action_type)
    if not spec:
        raise ActionError("Cette action n'existe pas.")
    if not frappe.has_permission(spec.doctype, spec.ptype):
        raise ActionError(f"Votre rôle ne permet pas de faire cette action ({spec.label.lower()}).")
    open_count = frappe.db.count(DOCTYPE, {"requested_by": user, "status": PROPOSED, "company": company})
    if open_count >= MAX_OPEN_PER_USER:
        raise ActionError("Trop de propositions en attente : approuvez ou refusez les précédentes.")
    prepared = spec.prepare(args or {}, company)
    doc = frappe.get_doc(
        {
            "doctype": DOCTYPE,
            "company": company,
            "requested_by": user,
            "action_type": action_type,
            "status": PROPOSED,
            "summary": prepared.summary[:140],
            "expires_at": _now() + timedelta(hours=LIFETIME_HOURS),
            "payload_json": json.dumps(prepared.payload, ensure_ascii=False),
            "preview_json": json.dumps(
                {"lines": prepared.lines, "signature": preview_signature(prepared.lines)}, ensure_ascii=False
            ),
        }
    )
    doc.flags.from_ai_actions = True
    doc.insert(ignore_permissions=True)
    _audit(company, "cortex.ai_action.proposed", doc.name, {"type": action_type, "summary": prepared.summary})
    return block_for({"name": doc.name, "label": spec.label, "summary": prepared.summary, "lines": prepared.lines})


def _finish(doc, status: str, user: str, result: Optional[Dict[str, Any]] = None, error: str = "") -> None:
    doc.status = status
    doc.decided_by = user
    doc.decided_at = _now()
    doc.result_json = json.dumps(result, ensure_ascii=False) if result else ""
    doc.error = error[:500]
    doc.flags.from_ai_actions = True
    doc.save(ignore_permissions=True)


def decide(name: str, approve: bool, company: str, user: str) -> Dict[str, Any]:
    """Approuve (et exécute) ou refuse. Seule la personne qui a demandé peut décider; l'exécution prend ses droits."""
    # Verrou sur la ligne : un double clic ou deux onglets n'exécutent qu'une fois.
    row = frappe.db.get_value(
        DOCTYPE, name, ["company", "requested_by", "status", "action_type", "expires_at"], as_dict=True, for_update=True
    )
    if not row or row.company != company or row.requested_by != user:
        raise ActionError("Cette proposition n'est pas disponible pour vous.")
    if row.status != PROPOSED:
        raise ActionError("Cette proposition a déjà été traitée.")
    doc = frappe.get_doc(DOCTYPE, name)
    spec = ACTIONS.get(row.action_type)
    if not spec:
        return _close(doc, FAILED, user, "Cette action n'existe plus.")
    if not approve:
        _finish(doc, REJECTED, user)
        _audit(company, "cortex.ai_action.rejected", name, {"type": row.action_type})
        return {"ok": True, "status": REJECTED, "message": "Proposition refusée. Rien n'a été fait."}
    if is_expired(row.expires_at, _now()):
        return _close(doc, EXPIRED, user, "Cette proposition a expiré. Demandez-la de nouveau à l'assistant.")
    payload = json.loads(doc.payload_json or "{}")
    shown = json.loads(doc.preview_json or "{}")
    try:
        fresh = spec.prepare(payload, company)  # même validation, mêmes droits, prix du moment
    except ActionError as exc:
        _audit(company, "cortex.ai_action.failed", name, {"type": row.action_type, "error": str(exc)})
        return _close(doc, FAILED, user, str(exc))
    if preview_signature(fresh.lines) != shown.get("signature"):
        _audit(company, "cortex.ai_action.stale", name, {"type": row.action_type})
        return _close(
            doc, EXPIRED, user, "Les prix ou les données ont changé depuis la proposition. Demandez-la de nouveau."
        )
    # Point de sauvegarde : une écriture partielle d'une exécution qui échoue ne reste jamais.
    frappe.db.savepoint(SAVEPOINT)
    try:
        result = spec.run(fresh.payload, company)
    except Exception as exc:  # noqa: BLE001 - un refus de droits ou de validation est dit tel quel, jamais présenté en succès
        frappe.db.rollback(save_point=SAVEPOINT)
        message = str(getattr(exc, "message", None) or exc)[:300]
        _audit(company, "cortex.ai_action.failed", name, {"type": row.action_type, "error": message})
        return _close(doc, FAILED, user, message)
    _finish(doc, EXECUTED, user, result=result)
    _audit(company, "cortex.ai_action.executed", name, {"type": row.action_type, "result": result})
    return {"ok": True, "status": EXECUTED, "message": f"{spec.label} : fait.", "result": result}


def _close(doc, status: str, user: str, message: str) -> Dict[str, Any]:
    """Note l'issue et la renvoie comme résultat (jamais une exception : elle annulerait la note elle-même)."""
    _finish(doc, status, user, error=message)
    return {"ok": False, "status": status, "message": message}
