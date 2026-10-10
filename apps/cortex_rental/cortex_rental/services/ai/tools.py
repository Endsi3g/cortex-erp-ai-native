"""Outils que l'assistant peut appeler. Chacun s'exécute avec les droits de la personne connectée (jamais un compte de
service) et dans sa société ; aucun ne confirme, n'approuve ni n'écrit : « proposer » ne crée rien.

Les noms suivent la liste d'autorisations par agent (`services/tool_policy.py`) ; un outil absent de cette liste n'est
jamais exposé au modèle.
"""

from contextvars import ContextVar
from typing import Any, Callable, Dict, List

from cortex_rental.services.ai import stats

try:
    import frappe
    from frappe.utils import flt, getdate, today
except ImportError:
    frappe = None

    def flt(value, precision=None):
        return round(float(value or 0), precision if precision is not None else 6)


class Tool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], fn: Callable[..., Any]):
        self.name, self.description, self.parameters, self.fn = name, description, parameters, fn

    def declaration(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


REGISTRY: Dict[str, Tool] = {}


def tool(name: str, description: str, properties: Dict[str, Any], required: List[str] = ()):
    def register(fn):
        REGISTRY[name] = Tool(
            name, description, {"type": "object", "properties": properties, "required": list(required)}, fn
        )
        return fn

    return register


def _company() -> str:
    from cortex_rental.permissions.agent_scopes import get_company_context

    return get_company_context()


STR = {"type": "string"}
DATETIME = {"type": "string", "description": "Date et heure au format AAAA-MM-JJ hh:mm:ss"}


@tool(
    "search_rental_items",
    "Cherche des équipements du catalogue de la société par nom ou code. Renvoie tarif journalier et parc.",
    {"query": {"type": "string", "description": "Mot ou code à chercher"}},
    ["query"],
)
def search_rental_items(query: str):
    company = _company()
    like = f"%{query.strip()}%"
    if not company:
        return {"items": []}
    # Toujours limité à la société de la personne : jamais de repli vers le catalogue d'une autre société.
    rows = frappe.get_list(
        "Cortex Rental Item Profile",
        filters={"company": company},
        or_filters=[["item_name", "like", like], ["item_code", "like", like]],
        fields=["item_code", "item_name", "category", "daily_rate", "total_quantity", "is_serialized"],
        limit_page_length=15,
    )
    return {"items": [dict(r) for r in rows]}


@tool(
    "check_inventory_availability",
    "Vérifie combien d'unités d'un équipement sont libres sur une période. Source : le serveur de disponibilité.",
    {"item_code": STR, "starts_at": DATETIME, "ends_at": DATETIME, "quantity": {"type": "number"}},
    ["item_code", "starts_at", "ends_at"],
)
def check_inventory_availability(item_code: str, starts_at: str, ends_at: str, quantity: float = 1):
    from cortex_rental.services.availability import AvailabilityService

    results = AvailabilityService().check(
        company=_company(),
        starts_at=starts_at,
        ends_at=ends_at,
        item_requests=[{"item_code": item_code, "quantity": quantity or 1}],
    )
    return {"results": results, "checked_at": str(frappe.utils.now_datetime())}


@tool(
    "search_customers",
    "Cherche un client de la société par nom.",
    {"query": {"type": "string", "description": "Début du nom du client"}},
    ["query"],
)
def search_customers(query: str):
    rows = frappe.get_list(
        "Customer",
        filters={"cortex_company": _company(), "customer_name": ["like", f"%{query.strip()}%"]},
        fields=["name", "customer_name"],
        limit_page_length=10,
    )
    return {"customers": [dict(r) for r in rows]}


@tool(
    "list_rentals",
    "Liste les locations récentes de la société, éventuellement d'un état donné (Quote, Reservation, Contract, Checked Out, Returned, Closed, Cancelled, Disputed).",
    {"state": STR, "limit": {"type": "integer"}},
)
def list_rentals(state: str = "", limit: int = 10):
    filters = {"company": _company()}
    if state:
        filters["rental_state"] = state
    rows = frappe.get_list(
        "Cortex Rental Transaction",
        filters=filters,
        fields=["name", "customer", "rental_state", "starts_at", "ends_at", "grand_total"],
        order_by="modified desc",
        limit_page_length=max(1, min(_as_int(limit, 10), 25)),
    )
    return {"rentals": [{**dict(r), "starts_at": str(r.starts_at), "ends_at": str(r.ends_at)} for r in rows]}


@tool(
    "list_pending_approvals",
    "Liste les demandes d'approbation en attente de décision humaine.",
    {"limit": {"type": "integer"}},
)
def list_pending_approvals(limit: int = 10):
    rows = frappe.get_list(
        "Approval Request",
        filters={"company": _company(), "status": "Pending"},
        fields=["name", "action", "entity_id", "requested_by_id", "creation"],
        order_by="creation desc",
        limit_page_length=max(1, min(_as_int(limit, 10), 25)),
    )
    return {"pending": [{**dict(r), "creation": str(r.creation)} for r in rows]}


@tool(
    "finance_summary", "Résumé financier du mois : facturé, encaissé, solde à recevoir, factures en retard, taxes.", {}
)
def finance_summary():
    if not frappe.has_permission("Cortex Rental Invoice", "read"):
        return {"error": "Vous n'avez pas accès aux données financières."}
    company = _company()
    first = getdate(today()).replace(day=1)
    invoiced = frappe.get_list(
        "Cortex Rental Invoice",
        filters={"company": company, "status": ["!=", "Cancelled"], "issue_date": [">=", first]},
        fields=["sum(total) as total", "sum(tps_amount) as tps", "sum(tvq_amount) as tvq"],
    )[0]
    open_invoices = frappe.get_list(
        "Cortex Rental Invoice",
        filters={"company": company, "status": ["in", ["Issued", "Partially Paid"]]},
        fields=["sum(balance) as balance", "count(name) as count"],
    )[0]
    overdue = frappe.get_list(
        "Cortex Rental Invoice",
        filters={"company": company, "status": ["in", ["Issued", "Partially Paid"]], "due_date": ["<", today()]},
        fields=["count(name) as count"],
    )[0]
    received = frappe.get_list(
        "Cortex Rental Payment",
        filters={"company": company, "paid_on": [">=", first]},
        fields=["sum(signed_amount) as total"],
    )[0]
    result = {
        "mois": str(first)[:7],
        "facture": flt(invoiced.total, 2),
        "tps": flt(invoiced.tps, 2),
        "tvq": flt(invoiced.tvq, 2),
        "encaisse": flt(received.total, 2),
        "solde_a_recevoir": flt(open_invoices.balance, 2),
        "factures_ouvertes": int(open_invoices.count or 0),
        "factures_en_retard": int(overdue.count or 0),
    }
    result["stat_block"] = stats.card(
        f"Finance — {result['mois']}",
        "Ouvrir Finance",
        "/app/cortex-finance",
        subtitle="Mois en cours (partiel)",
        kpis=[
            stats.kpi_block("Facturé", stats.money(result["facture"])),
            stats.kpi_block("Encaissé", stats.money(result["encaisse"]), tone="good"),
            stats.kpi_block(
                "Solde à recevoir", stats.money(result["solde_a_recevoir"]), f"{result['factures_ouvertes']} facture(s)"
            ),
            stats.kpi_block(
                "Factures en retard",
                str(result["factures_en_retard"]),
                tone="bad" if result["factures_en_retard"] else "good",
            ),
        ],
        checked_at=str(frappe.utils.now_datetime()),
    )
    return result


@tool(
    "finance_trend",
    "Évolution mensuelle du facturé et de l'encaissé sur les derniers mois (3 à 12). Affiche un graphique à la personne.",
    {"months": {"type": "integer", "description": "Nombre de mois, de 3 à 12 (6 par défaut)"}},
)
def finance_trend(months: int = 6):
    if not frappe.has_permission("Cortex Rental Invoice", "read"):
        return {"error": "Vous n'avez pas accès aux données financières."}
    count = max(3, min(_as_int(months, 6), 12))
    now = frappe.utils.now_datetime()
    today_tuple = (now.year, now.month, now.day)
    span = stats.last_months(today_tuple, count)[0]
    start = f"{span[0]:04d}-{span[1]:02d}-01"
    company = _company()
    invoices = frappe.get_list(
        "Cortex Rental Invoice",
        filters={"company": company, "status": ["!=", "Cancelled"], "issue_date": [">=", start]},
        fields=["issue_date", "total"],
        limit_page_length=0,
    )
    payments = frappe.get_list(
        "Cortex Rental Payment",
        filters={"company": company, "paid_on": [">=", start]},
        fields=["paid_on", "signed_amount"],
        limit_page_length=0,
    )
    labels, invoiced = stats.monthly_totals(invoices, today_tuple, count, "total", "issue_date")
    _, received = stats.monthly_totals(payments, today_tuple, count, "signed_amount", "paid_on")
    return {
        "mois": labels,
        "facture": invoiced,
        "encaisse": received,
        "stat_block": stats.card(
            "Facturé par mois",
            "Ouvrir Finance",
            "/app/cortex-finance",
            subtitle=f"{count} derniers mois · le mois en cours est partiel",
            kpis=[
                stats.kpi_block("Total facturé", stats.money(sum(invoiced))),
                stats.kpi_block("Total encaissé", stats.money(sum(received)), tone="good"),
            ],
            series=stats.series_block("bar", labels, invoiced, "$"),
            checked_at=str(now),
        ),
    }


@tool(
    "rentals_by_state",
    "Nombre de locations de la société par état (Devis, Réservation, Contrat, Sortie, Retournée…). Affiche un graphique à la personne.",
    {},
)
def rentals_by_state():
    if not frappe.has_permission("Cortex Rental Transaction", "read"):
        return {"error": "Vous n'avez pas accès aux locations."}
    rows = frappe.get_list(
        "Cortex Rental Transaction",
        filters={"company": _company()},
        fields=["rental_state", "count(name) as n"],
        group_by="rental_state",
        limit_page_length=0,
    )
    counts = {r.rental_state: int(r.n or 0) for r in rows}
    order = [s for s in stats.STATE_ORDER if s in counts] + [s for s in counts if s not in stats.STATE_ORDER]
    labels = [stats.STATE_LABELS.get(s, s) for s in order]
    return {
        "par_etat": {stats.STATE_LABELS.get(s, s): counts[s] for s in order},
        "stat_block": stats.card(
            "Locations par état",
            "Ouvrir les locations",
            "/app/cortex-rental-transaction",
            subtitle="Toutes les locations de la société",
            series=stats.series_block("donut", labels, [counts[s] for s in order], "locations"),
            checked_at=str(frappe.utils.now_datetime()),
        ),
    }


@tool(
    "customer_summary",
    "Résume un client : devis ouverts, locations en cours, retours en retard, solde dû et dernière location.",
    {"customer": {"type": "string", "description": "Identifiant exact du client (utiliser search_customers)"}},
    ["customer"],
)
def customer_summary(customer: str):
    from cortex_rental.services import customer_360

    return customer_360.summary(customer, _company())


@tool(
    "late_returns",
    "Liste les retours en retard : locations sorties dont la date de fin est passée.",
    {"limit": {"type": "integer"}},
)
def late_returns(limit: int = 10):
    rows = frappe.get_list(
        "Cortex Rental Transaction",
        filters={
            "company": _company(),
            "rental_state": ["in", ["Checked Out", "Partially Returned"]],
            "ends_at": ["<", frappe.utils.now_datetime()],
        },
        fields=["name", "customer", "ends_at", "grand_total"],
        order_by="ends_at asc",
        limit_page_length=max(1, min(_as_int(limit, 10), 25)),
    )
    return {"late": [{**dict(r), "ends_at": str(r.ends_at)} for r in rows]}


@tool(
    "create_quote_draft",
    "PROPOSE un devis (prix calculés par le serveur). Ne crée rien : la personne ouvre le compositeur et décide.",
    {
        "customer": {"type": "string", "description": "Nom exact du client (utiliser search_customers)"},
        "starts_at": DATETIME,
        "ends_at": DATETIME,
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"item_code": STR, "quantity": {"type": "number"}},
                "required": ["item_code", "quantity"],
            },
        },
    },
    ["customer", "starts_at", "ends_at", "items"],
)
def create_quote_draft(customer: str, starts_at: str, ends_at: str, items: List[Dict[str, Any]]):
    from cortex_rental.api.v1.rentals import _customer_in_company, _pricing
    from cortex_rental.services import billing

    company = _company()
    _customer_in_company(customer, company)
    priced = _pricing(
        {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "items": [{"item_code": i["item_code"], "quantity": i["quantity"]} for i in items],
        },
        company,
    )
    settings = billing.get_settings(company)
    tps, tvq = billing.compute_taxes(priced["subtotal"], settings)
    return {
        "proposal": {
            "customer": customer,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "billable_days": priced["billable_days"],
            "lines": [
                {
                    "item": l["item_name"],
                    "quantity": l["quantity"],
                    "daily_rate": l["daily_rate"],
                    "amount": l["line_subtotal"],
                }
                for l in priced["lines"]
            ],
            "subtotal": priced["subtotal"],
            "tps": tps,
            "tvq": tvq,
            "total": round(priced["subtotal"] + tps + tvq, 2),
        },
        "note": "Proposition seulement : aucun devis n'a été créé.",
    }


# Libellés des outils de lecture déjà appelés dans ce tour : l'assistant les montre dans « Pourquoi cette proposition ».
# Posé par la passerelle (gateway.py) à chaque tour; vide hors passerelle.
CONSULTED: ContextVar = ContextVar("cortex_ai_consulted", default=None)

REASON = {
    "type": "string",
    "description": "Pourquoi tu proposes cette action, en une ou deux phrases claires pour la personne (ce que tu as constaté, ce que tu cherches à faire).",
}


def _propose(action_type: str, args: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    from cortex_rental.services.ai import actions

    if not actions_enabled():
        return {"error": "Les actions de l'assistant ne sont pas activées sur ce site."}
    try:
        block = actions.propose(
            action_type, args, _company(), frappe.session.user, reason=reason, checks=tuple(CONSULTED.get() or ())
        )
    except actions.ActionError as exc:
        return {"error": str(exc)}
    return {
        "action_block": block,
        "note": "Proposition affichée à la personne. Rien n'est fait tant qu'elle n'approuve pas : ne dis jamais que c'est fait.",
    }


def _proposing_tool(name: str, action_type: str, description: str, properties: Dict[str, Any], required: List[str]):
    """Déclare un outil « propose_* » : il passe par `actions.propose` et n'écrit jamais lui-même."""

    def run(reason: str = "", **args):
        return _propose(action_type, args, reason)

    run.__name__ = name
    props = {**properties, "reason": REASON}
    tool(
        name,
        description + " La personne voit un aperçu et approuve ou refuse; rien n'est fait avant son approbation.",
        props,
        required,
    )(run)
    return run


propose_create_customer = _proposing_tool(
    "propose_create_customer",
    "create_customer",
    "PROPOSE de créer un client.",
    {
        "customer_name": {
            "type": "string",
            "description": "Nom du client (utiliser search_customers d'abord pour éviter un doublon)",
        }
    },
    ["customer_name"],
)
propose_create_quote = _proposing_tool(
    "propose_create_quote",
    "create_quote",
    "PROPOSE de créer un devis (prix calculés par le serveur). Vérifie d'abord le client et la disponibilité.",
    {
        "customer": {"type": "string", "description": "Identifiant exact du client (utiliser search_customers)"},
        "starts_at": DATETIME,
        "ends_at": DATETIME,
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"item_code": STR, "quantity": {"type": "number"}},
                "required": ["item_code", "quantity"],
            },
        },
    },
    ["customer", "starts_at", "ends_at", "items"],
)
RENTAL = {"rental": {"type": "string", "description": "Identifiant exact de la location (utiliser list_rentals)"}}
propose_release_hold = _proposing_tool(
    "propose_release_hold", "release_hold", "PROPOSE de libérer la retenue de matériel d'un devis.", RENTAL, ["rental"]
)
propose_renew_hold = _proposing_tool(
    "propose_renew_hold", "renew_hold", "PROPOSE de renouveler la retenue de matériel d'un devis.", RENTAL, ["rental"]
)
propose_request_reservation = _proposing_tool(
    "propose_request_reservation",
    "request_reservation",
    "PROPOSE de transformer un devis en réservation (la disponibilité est vérifiée).",
    RENTAL,
    ["rental"],
)
propose_record_payment = _proposing_tool(
    "propose_record_payment",
    "record_payment",
    "PROPOSE d'enregistrer un paiement DÉJÀ REÇU sur une facture (ne prélève rien).",
    {
        "invoice": {"type": "string", "description": "Identifiant exact de la facture"},
        "amount": {"type": "number", "description": "Montant reçu, en dollars"},
        "method": {"type": "string", "description": "Card, Cash, Bank Transfer, Cheque ou Other"},
        "reference": {
            "type": "string",
            "description": "Référence du paiement (numéro de chèque, de virement…), facultatif",
        },
    },
    ["invoice", "amount"],
)
propose_decide_approval = _proposing_tool(
    "propose_decide_approval",
    "decide_approval",
    "PROPOSE d'approuver ou de refuser une demande d'approbation en attente (utiliser list_pending_approvals).",
    {
        "approval": {"type": "string", "description": "Identifiant exact de la demande"},
        "decision": {"type": "string", "description": "approve ou reject"},
        "decision_reason": {"type": "string", "description": "Motif de la décision (obligatoire pour un refus)"},
    },
    ["approval", "decision"],
)


# Outils qui proposent une écriture (approbation humaine requise). Offerts au modèle seulement si le site les active :
# clé `cortex_ai_actions` de la configuration du site (éteinte par défaut tant que l'affichage des propositions n'est pas validé).
PROPOSING_TOOLS = (
    "propose_create_customer",
    "propose_create_quote",
    "propose_release_hold",
    "propose_renew_hold",
    "propose_request_reservation",
    "propose_record_payment",
    "propose_decide_approval",
)


def actions_enabled() -> bool:
    return bool(frappe and frappe.conf.get("cortex_ai_actions"))


def exposed(allowed_names: List[str]) -> List[Tool]:
    """Les outils réellement offerts au modèle : ceux de la liste d'autorisations qui existent dans le registre."""
    allow_proposals = actions_enabled()
    return [
        REGISTRY[name]
        for name in allowed_names
        if name in REGISTRY and (allow_proposals or name not in PROPOSING_TOOLS)
    ]


def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute un outil sous les droits de la personne ; une erreur devient un résultat lisible par le modèle."""
    spec = REGISTRY.get(name)
    if not spec:
        return {"error": f"Outil inconnu : {name}"}
    try:
        return spec.fn(**{k: v for k, v in (args or {}).items()})
    except TypeError:
        return {"error": "Paramètres invalides pour cet outil."}
    except Exception as exc:  # noqa: BLE001 - toute erreur (droits, validation) est renvoyée au modèle, jamais masquée en succès
        message = getattr(exc, "message", None) or str(exc)
        return {"error": str(message)[:300]}


def _as_int(value, default: int) -> int:
    """Les arguments des outils viennent du modèle : un nombre mal formé ne doit jamais faire échouer l'outil."""
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError, OverflowError):
        return default
