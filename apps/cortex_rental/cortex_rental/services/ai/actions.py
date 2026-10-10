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
from typing import Any, Callable, Dict, List, Optional, Tuple

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
    """Ce qu'une action valide : les données propres, un résumé et l'aperçu (ce que la personne approuve).

    `lines` (texte) fonde l'empreinte de l'aperçu; `rows` et `totals` sont les mêmes informations en structure, pour la carte."""

    payload: Dict[str, Any]
    summary: str
    lines: List[str]
    rows: Optional[List[Dict[str, Any]]] = None
    totals: Optional[List[Dict[str, Any]]] = None
    subtitle: str = ""
    approve_label: str = "Approuver"


@dataclass
class ActionSpec:
    name: str
    label: str  # « Créer un client »
    doctype: str  # droit vérifié avant même de proposer
    ptype: str
    prepare: Callable[[Dict[str, Any], str], Prepared]
    run: Callable[[Dict[str, Any], str], Dict[str, Any]]
    # Ce qui va se passer, ce qui ne se passera pas et comment revenir en arrière : montré dans « Pourquoi cette proposition ».
    effects: Tuple[str, ...] = ()


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
    """Pur : la carte d'action (bloc `action_card`) qui présente la proposition dans la conversation."""
    return {
        "type": "action_card",
        "action_id": record["name"],
        "action_type": record["action_type"],
        "title": record["label"],
        "subtitle": record.get("subtitle") or record.get("summary") or None,
        "rows": list(record.get("rows") or [{"label": line} for line in record.get("lines", [])]),
        "totals": list(record.get("totals") or []),
        "status": record.get("status", "Proposed"),
        "approve_label": record.get("approve_label") or "Approuver",
        "message": record.get("message") or None,
        "result_label": record.get("result_label") or None,
        "result_href": record.get("result_href") or None,
        "reasoning": record.get("reasoning") or None,
    }


def clean_reason(value: Any) -> str:
    """Pur : la raison déclarée par l'assistant, sans espaces superflus, 600 caractères au plus."""
    return " ".join(str(value or "").split())[:600]


def reasoning_for(spec_effects: Any, stated: Any = "", checks: Any = ()) -> Optional[Dict[str, Any]]:
    """Pur : « Pourquoi cette proposition » = l'explication de l'assistant (non vérifiée), ce qu'il a réellement consulté
    (outils appelés dans ce tour) et ce que l'action fera ou ne fera pas. Rien de tout cela n'est du texte inventé ici."""
    text = clean_reason(stated)
    seen, done = set(), []
    for label in checks or ():
        if label and label not in seen:
            seen.add(label)
            done.append(str(label))
    effects = [str(e) for e in spec_effects or ()]
    if not (text or done or effects):
        return None
    return {"stated": text or None, "checks": done, "effects": effects}


def href_for(doctype: str, name: str) -> str:
    """Pur : chemin du Desk d'un document (« /app/customer/CUST-1 »), sûr à mettre dans un lien."""
    from urllib.parse import quote

    from cortex_rental.services.ai.stats import safe_href

    return safe_href(f"/app/{doctype.lower().replace(' ', '-')}/{quote(str(name), safe='')}")


# --- Actions (chaque écriture passe par la fonction de l'écran correspondant) ----------------------------------------


def _prepare_customer(args: Dict[str, Any], company: str) -> Prepared:
    from cortex_rental.api.v1.customers import clean_customer_name

    try:
        name = clean_customer_name(args.get("customer_name"))
    except ValueError as exc:
        raise ActionError(str(exc))
    if frappe.db.exists("Customer", {"cortex_company": company, "customer_name": name}):
        raise ActionError(f"Un client « {name} » existe déjà.")
    return Prepared(
        {"customer_name": name},
        f"Nouveau client : {name}",
        [f"Client à créer : {name}"],
        rows=[{"label": "Nom du client", "value": name}],
        subtitle="Ajouté à la liste des clients de votre société",
        approve_label="Créer le client",
    )


def _run_customer(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    from cortex_rental.api.v1.customers import insert_customer

    doc = insert_customer(company, payload["customer_name"])
    return {"id": doc.name, "label": "Ouvrir la fiche du client", "href": href_for("Customer", doc.name)}


def _prepare_quote(args: Dict[str, Any], company: str) -> Prepared:
    from cortex_rental.services.ai.stats import fr_number, human_dt, money
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
    lines = [f"{l['item_name']} × {l['quantity']:g} — {money(l['line_subtotal'])}" for l in priced["lines"]]
    lines.append(f"Sous-total {money(priced['subtotal'])} · TPS {money(tps)} · TVQ {money(tvq)}")
    payload = {
        "customer_id": customer,
        "starts_at": str(args.get("starts_at")),
        "ends_at": str(args.get("ends_at")),
        "items": [{"item_code": l["item_code"], "quantity": l["quantity"]} for l in priced["lines"]],
        "notes": "Proposé par l'assistant, approuvé par une personne.",
    }
    period = f"{human_dt(payload['starts_at'])} → {human_dt(payload['ends_at'])}"
    rows = [
        {
            "label": l["item_name"],
            "detail": f"× {fr_number(l['quantity'])} · {money(l['daily_rate'])} par jour",
            "value": money(l["line_subtotal"]),
        }
        for l in priced["lines"]
    ]
    total = round(priced["subtotal"] + tps + tvq, 2)
    totals = [
        {"label": "Sous-total", "value": money(priced["subtotal"])},
        {"label": "TPS", "value": money(tps)},
        {"label": "TVQ", "value": money(tvq)},
        {"label": "Total", "value": money(total)},
    ]
    return Prepared(
        payload,
        f"Devis pour {customer} · {period}",
        lines,
        rows=rows,
        totals=totals,
        subtitle=f"{customer} · {period} · {fr_number(priced['billable_days'])} jour(s) facturable(s)",
        approve_label="Créer le devis",
    )


def _run_quote(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    from cortex_rental.api.v1.rentals import _pricing, insert_quote

    priced = _pricing(payload, company)  # les prix sont recalculés par le serveur au moment d'écrire
    name = insert_quote(company, payload, priced)
    return {"id": name, "label": "Ouvrir le devis", "href": href_for("Cortex Rental Transaction", name)}


register(
    ActionSpec(
        "create_customer",
        "Créer un client",
        "Customer",
        "create",
        _prepare_customer,
        _run_customer,
        effects=(
            "Ajoute ce client à la liste des clients de votre société.",
            "Rien n'est envoyé au client et aucun devis n'est créé.",
            "Pour revenir en arrière : désactiver la fiche du client (elle ne se supprime pas si elle est utilisée).",
        ),
    )
)
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


def propose(
    action_type: str,
    args: Dict[str, Any],
    company: str,
    user: str,
    session: str = "",
    reason: str = "",
    checks: Tuple[str, ...] = (),
) -> Dict[str, Any]:
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
                {
                    "lines": prepared.lines,
                    "signature": preview_signature(prepared.lines),
                    "rows": prepared.rows,
                    "totals": prepared.totals,
                    "subtitle": prepared.subtitle,
                    "approve_label": prepared.approve_label,
                },
                ensure_ascii=False,
            ),
        }
    )
    doc.flags.from_ai_actions = True
    doc.insert(ignore_permissions=True)
    _audit(company, "cortex.ai_action.proposed", doc.name, {"type": action_type, "summary": prepared.summary})
    return block_for(
        {
            "name": doc.name,
            "action_type": action_type,
            "label": spec.label,
            "summary": prepared.summary,
            "lines": prepared.lines,
            "rows": prepared.rows,
            "totals": prepared.totals,
            "subtitle": prepared.subtitle,
            "approve_label": prepared.approve_label,
            "reasoning": reasoning_for(spec.effects, reason, checks),
        }
    )


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
        try:
            frappe.db.rollback(save_point=SAVEPOINT)
        except Exception:
            # Certaines écritures (ex. retenue de devis) valident elles-mêmes la transaction : le point de sauvegarde n'existe plus.
            frappe.log_error(title="Cortex AI action rollback impossible")
        message = str(getattr(exc, "message", None) or exc)[:300]
        _audit(company, "cortex.ai_action.failed", name, {"type": row.action_type, "error": message})
        return _close(doc, FAILED, user, message)
    _finish(doc, EXECUTED, user, result=result)
    _audit(company, "cortex.ai_action.executed", name, {"type": row.action_type, "result": result})
    return {
        "ok": True,
        "status": EXECUTED,
        "message": f"{spec.label} : fait.",
        "result_label": result.get("label"),
        "result_href": result.get("href"),
    }


def _close(doc, status: str, user: str, message: str) -> Dict[str, Any]:
    """Note l'issue et la renvoie comme résultat (jamais une exception : elle annulerait la note elle-même)."""
    _finish(doc, status, user, error=message)
    return {"ok": False, "status": status, "message": message}


def refresh_blocks(blocks: List[Dict[str, Any]], user: str) -> List[Dict[str, Any]]:
    """Au rechargement d'une conversation, remet à jour l'état de chaque carte d'action (exécutée, refusée, périmée…).

    Sans cela, une carte déjà approuvée redeviendrait « à approuver » : le serveur est la seule source de l'état."""
    out = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "action_card":
            out.append(block)
            continue
        row = frappe.db.get_value(
            DOCTYPE,
            block.get("action_id"),
            ["status", "requested_by", "result_json", "error", "expires_at"],
            as_dict=True,
        )
        if not row or row.requested_by != user:
            out.append({**block, "status": "Expired", "message": "Cette proposition n'est plus disponible."})
            continue
        status = row.status
        if status == PROPOSED and is_expired(row.expires_at, _now()):
            status = EXPIRED
        result = json.loads(row.result_json) if row.result_json else {}
        out.append(
            {
                **block,
                "status": status,
                "message": (row.error or None) if status in (FAILED, EXPIRED) else None,
                "result_label": result.get("label"),
                "result_href": result.get("href"),
            }
        )
    return out


# Les actions du catalogue (retenue, réservation, paiement, approbation) s'enregistrent à l'import.
from cortex_rental.services.ai import action_catalog  # noqa: E402,F401
