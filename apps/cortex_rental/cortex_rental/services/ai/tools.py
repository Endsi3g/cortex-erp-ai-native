"""Outils que l'assistant peut appeler. Chacun s'exécute avec les droits de la personne connectée (jamais un compte de
service) et dans sa société ; aucun ne confirme, n'approuve ni n'écrit : « proposer » ne crée rien.

Les noms suivent la liste d'autorisations par agent (`services/tool_policy.py`) ; un outil absent de cette liste n'est
jamais exposé au modèle.
"""

from typing import Any, Callable, Dict, List

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
    return {
        "mois": str(first)[:7],
        "facture": flt(invoiced.total, 2),
        "tps": flt(invoiced.tps, 2),
        "tvq": flt(invoiced.tvq, 2),
        "encaisse": flt(received.total, 2),
        "solde_a_recevoir": flt(open_invoices.balance, 2),
        "factures_ouvertes": int(open_invoices.count or 0),
        "factures_en_retard": int(overdue.count or 0),
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


def _propose(action_type: str, args: Dict[str, Any]) -> Dict[str, Any]:
    from cortex_rental.services.ai import actions

    if not actions_enabled():
        return {"error": "Les actions de l'assistant ne sont pas activées sur ce site."}
    try:
        block = actions.propose(action_type, args, _company(), frappe.session.user)
    except actions.ActionError as exc:
        return {"error": str(exc)}
    return {
        "action_block": block,
        "note": "Proposition affichée à la personne. Rien n'est fait tant qu'elle n'approuve pas : ne dis jamais que c'est fait.",
    }


@tool(
    "propose_create_customer",
    "PROPOSE de créer un client. La personne voit un aperçu et approuve ou refuse; rien n'est créé avant son approbation.",
    {
        "customer_name": {
            "type": "string",
            "description": "Nom du client (utiliser search_customers d'abord pour éviter un doublon)",
        }
    },
    ["customer_name"],
)
def propose_create_customer(customer_name: str):
    return _propose("create_customer", {"customer_name": customer_name})


@tool(
    "propose_create_quote",
    "PROPOSE de créer un devis (prix calculés par le serveur). La personne voit l'aperçu et approuve ou refuse; rien n'est créé avant son approbation. Vérifie d'abord le client et la disponibilité.",
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
def propose_create_quote(customer: str, starts_at: str, ends_at: str, items: List[Dict[str, Any]]):
    return _propose("create_quote", {"customer": customer, "starts_at": starts_at, "ends_at": ends_at, "items": items})


# Outils qui proposent une écriture (approbation humaine requise). Offerts au modèle seulement si le site les active :
# clé `cortex_ai_actions` de la configuration du site (éteinte par défaut tant que l'affichage des propositions n'est pas validé).
PROPOSING_TOOLS = ("propose_create_customer", "propose_create_quote")


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
