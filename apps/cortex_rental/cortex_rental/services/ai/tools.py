"""The tools the Cortex assistant can use.

Every tool wraps an existing Cortex endpoint or handler and runs as the
signed-in person: the endpoint's own role and company checks apply, so
the assistant can never read or do more than the user could on screen.

- Read tools run immediately and return data (plus an optional `view`
  hint the UI renders as a widget or an artifact).
- Write tools never run from the model. They return a proposal the
  person confirms in the conversation (see engine.py / Cortex AI Action).
"""

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

MAX_RESULT_CHARS = 12000


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    kind: str  # "read" | "write" | "ui"
    handler: Optional[Callable[[Dict[str, Any], "ToolContext"], Any]] = None
    # write tools: short human summary of what confirming will do
    describe: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    roles: Optional[set] = None  # restrict offering the tool; endpoints still enforce

    def spec(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


@dataclass
class ToolContext:
    user: str
    company: str
    roles: set = field(default_factory=set)


class ToolError(Exception):
    """A tool failed in a way the model should see and explain."""


def call_endpoint(fn: Callable, **kwargs: Any) -> Any:
    """
    Call a whitelisted endpoint in-process: arguments it declares are passed
    directly, and form_dict is set for endpoints that read their payload
    from the request. The endpoint's own permission checks still run.
    """
    params = inspect.signature(fn).parameters
    direct = {k: v for k, v in kwargs.items() if k in params and v is not None}
    previous = getattr(frappe.local, "form_dict", None)
    frappe.local.form_dict = frappe._dict({k: v for k, v in kwargs.items() if v is not None})
    try:
        result = fn(**direct)
    finally:
        frappe.local.form_dict = previous
    return result.get("data", result) if isinstance(result, dict) else result


def compact(value: Any) -> str:
    """JSON for the model, truncated so one large report cannot flood the context."""
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + '… [tronqué : demander un filtre plus précis]"'
    return text


def _obj(properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


STR = {"type": "string"}
DATE = {"type": "string", "description": "Date ISO AAAA-MM-JJ"}
DATETIME = {"type": "string", "description": "Date-heure ISO AAAA-MM-JJTHH:MM"}
ITEMS = {
    "type": "array",
    "items": _obj({"item_code": STR, "quantity": {"type": "number"}}, ["item_code", "quantity"]),
}
FINANCE_ROLES = {
    "System Manager",
    "Cortex System Manager",
    "Cortex Operations Manager",
    "Cortex Finance Manager",
    "Cortex Account Reviewer",
    "Rental Manager",
}


def _mod(name: str):
    import importlib

    return importlib.import_module(f"cortex_rental.api.v1.{name}")


# ---- read handlers -----------------------------------------------------------------


def _search_customers(args, ctx):
    data = call_endpoint(_mod("clients").list_customers, search=args.get("query"), page_size=10)
    return {"data": data["items"], "view": {"type": "table", "entity": "customers"}}


def _get_customer(args, ctx):
    data = call_endpoint(_mod("clients").get_customer, customer=args["customer"])
    return {"data": data, "view": {"type": "record", "entity": "customer", "id": data["name"]}}


def _search_equipment(args, ctx):
    data = call_endpoint(
        _mod("catalog").list_equipment, search=args.get("query"), category=args.get("category"), page_size=20
    )
    return {"data": data["items"], "view": {"type": "table", "entity": "equipment"}}


def _get_equipment(args, ctx):
    data = call_endpoint(_mod("catalog").get_equipment, item_code=args["item_code"])
    if len(data.get("serials") or []) > 50:
        data["serials"] = data["serials"][:50]
    return {"data": data, "view": {"type": "record", "entity": "equipment", "id": data["item_code"]}}


def _check_availability(args, ctx):
    from cortex_rental.api.v1.availability import check_availability_handler

    results = check_availability_handler(
        {"starts_at": args["starts_at"], "ends_at": args["ends_at"], "items": args["items"]}, ctx.company
    )
    return {
        "data": results,
        "view": {
            "type": "availability",
            "items": [i["item_code"] for i in args["items"]],
            "starts_at": args["starts_at"],
            "ends_at": args["ends_at"],
        },
    }


def _preview_price(args, ctx):
    from cortex_rental.api.v1.rentals import _pricing

    data = _pricing({"starts_at": args["starts_at"], "ends_at": args["ends_at"], "items": args["items"]}, ctx.company)
    return {
        "data": data,
        "view": {
            "type": "pricing",
            "items": [i["item_code"] for i in args["items"]],
            "quantities": [i["quantity"] for i in args["items"]],
            "starts_at": args["starts_at"],
            "ends_at": args["ends_at"],
        },
    }


def _list_rentals(args, ctx):
    data = call_endpoint(
        _mod("rentals").list_rental_summaries,
        state=args.get("state"),
        search=args.get("search"),
        starts_from=args.get("starts_from"),
        starts_to=args.get("starts_to"),
        page_size=25,
    )
    return {"data": data, "view": {"type": "table", "entity": "rentals"}}


def _get_rental(args, ctx):
    data = call_endpoint(_mod("rentals").get_rental, name=args["rental"])
    return {"data": data, "view": {"type": "record", "entity": "rental", "id": args["rental"]}}


def _operations_overview(args, ctx):
    data = call_endpoint(_mod("operations").get_operations_overview, day=args.get("day"))
    return {"data": data, "view": {"type": "kpis", "entity": "operations"}}


def _profit_and_loss(args, ctx):
    report = call_endpoint(
        _mod("accounting").get_profit_and_loss,
        filter_based_on="Date Range",
        from_date=args["from_date"],
        to_date=args["to_date"],
        periodicity=args.get("periodicity") or "Monthly",
    )

    def top(rows):
        # Totals plus first-level accounts: enough to answer, small enough for the model.
        return [
            {
                "name": r.get("name"),
                "total": r.get("total"),
                "children": [{"name": c.get("name"), "total": c.get("total")} for c in r.get("children") or []],
            }
            for r in rows or []
        ]

    keys = (
        "available",
        "reason",
        "company",
        "currency",
        "periodStart",
        "periodEnd",
        "totalIncome",
        "totalExpense",
        "netProfit",
    )
    data = {k: report.get(k) for k in keys}
    data["accounts"] = top(report.get("accounts"))
    return {
        "data": data,
        "view": {"type": "report", "entity": "pnl", "from_date": args["from_date"], "to_date": args["to_date"]},
    }


def _list_invoices(args, ctx):
    data = call_endpoint(
        _mod("billing").list_invoices, status=args.get("status"), search=args.get("search"), page_size=25
    )
    return {"data": data, "view": {"type": "table", "entity": "invoices"}}


def _rental_billing(args, ctx):
    data = call_endpoint(_mod("billing").get_rental_billing, rental_id=args["rental"])
    return {"data": data, "view": {"type": "record", "entity": "rental_billing", "id": args["rental"]}}


def _consignment_dashboard(args, ctx):
    data = call_endpoint(_mod("consignment").get_dashboard, period=args.get("period"))
    return {"data": data, "view": {"type": "kpis", "entity": "consignment"}}


def _owner_statement(args, ctx):
    data = call_endpoint(_mod("consignment").get_owner_statement, owner=args["owner"], period=args["period"])
    return {
        "data": data,
        "view": {"type": "record", "entity": "owner_statement", "id": args["owner"], "period": args["period"]},
    }


def _ai_inbox(args, ctx):
    data = call_endpoint(_mod("ai").list_inbox, kind=args.get("kind"))
    return {"data": data["items"], "view": {"type": "table", "entity": "inbox"}}


def _pricing_policies(args, ctx):
    data = call_endpoint(_mod("admin").get_policies)
    return {
        "data": {"curve": data["curve"], "rules": data["rules"], "settings": data["settings"]},
        "view": {"type": "kpis", "entity": "policies"},
    }


def _open_page(args, ctx):
    return {"data": {"route": args["route"]}, "view": {"type": "link", "route": args["route"], "label": args["label"]}}


# ---- write proposals ------------------------------------------------------------------


def _describe_quote(args):
    lines = ", ".join(f"{i['quantity']} × {i['item_code']}" for i in args.get("items") or [])
    return {
        "title": f"Créer une soumission pour {args.get('customer_id')}",
        "impact": [f"Période : {args.get('starts_at')} → {args.get('ends_at')}", f"Articles : {lines}"],
        "effect": "Crée une location à l’état Soumission. Les prix viennent du catalogue. Rien n’est réservé.",
    }


WRITE_TOOLS = [
    Tool(
        "create_quote",
        "Proposer la création d'une soumission (location à l'état Quote). N'est exécuté qu'après confirmation.",
        _obj(
            {
                "customer_id": STR,
                "starts_at": DATETIME,
                "ends_at": DATETIME,
                "items": ITEMS,
                "project_name": STR,
                "notes": STR,
            },
            ["customer_id", "starts_at", "ends_at", "items"],
        ),
        "write",
        describe=_describe_quote,
    ),
    Tool(
        "confirm_reservation",
        "Proposer de passer une soumission à l'état Réservation (crée la commande client ERPNext).",
        _obj({"rental": STR}, ["rental"]),
        "write",
        describe=lambda a: {
            "title": f"Réserver {a.get('rental')}",
            "impact": ["Crée et soumet la commande client ERPNext", "Bloque le matériel sur la période"],
            "effect": "Passe la location à l’état Réservation, avec les contrôles habituels.",
        },
    ),
    Tool(
        "record_advance_payment",
        "Proposer d'enregistrer un acompte reçu pour une location.",
        _obj(
            {"rental": STR, "amount": {"type": "number"}, "mode_of_payment": STR, "reference_no": STR},
            ["rental", "amount", "mode_of_payment"],
        ),
        "write",
        describe=lambda a: {
            "title": f"Acompte de {a.get('amount')} sur {a.get('rental')}",
            "impact": [f"Mode : {a.get('mode_of_payment')}", f"Référence : {a.get('reference_no') or '—'}"],
            "effect": "Crée un Payment Entry ERPNext contre la commande client.",
        },
        roles=FINANCE_ROLES,
    ),
    Tool(
        "create_final_invoice",
        "Proposer de créer la facture de solde d'une location retournée.",
        _obj({"rental": STR}, ["rental"]),
        "write",
        describe=lambda a: {
            "title": f"Facture de solde pour {a.get('rental')}",
            "impact": ["Déduit les acomptes", "Ajoute dommages et pertes constatés au retour"],
            "effect": "Crée la Sales Invoice ERPNext de solde.",
        },
        roles=FINANCE_ROLES,
    ),
    Tool(
        "cancel_rental",
        "Proposer d'annuler une location, avec un motif.",
        _obj({"rental": STR, "reason": STR}, ["rental", "reason"]),
        "write",
        describe=lambda a: {
            "title": f"Annuler {a.get('rental')}",
            "impact": [f"Motif : {a.get('reason')}"],
            "effect": "Annule la location et ferme la commande client liée.",
        },
    ),
    Tool(
        "set_serial_status",
        "Proposer de changer le statut d'un numéro de série (Active, Quarantine, Under Repair, Missing, Decommissioned).",
        _obj({"serial_no": STR, "status": STR, "reason": STR}, ["serial_no", "status", "reason"]),
        "write",
        describe=lambda a: {
            "title": f"{a.get('serial_no')} → {a.get('status')}",
            "impact": [f"Motif : {a.get('reason')}"],
            "effect": "Change le statut opérationnel du numéro de série.",
        },
    ),
    Tool(
        "create_customer",
        "Proposer de créer un client ERPNext dans la société active.",
        _obj(
            {
                "customer_name": STR,
                "customer_type": {"type": "string", "enum": ["Company", "Individual"]},
                "email": STR,
                "phone": STR,
            },
            ["customer_name"],
        ),
        "write",
        describe=lambda a: {
            "title": f"Créer le client {a.get('customer_name')}",
            "impact": [f"Courriel : {a.get('email') or '—'}", f"Téléphone : {a.get('phone') or '—'}"],
            "effect": "Crée un Customer ERPNext rattaché à la société.",
        },
    ),
    Tool(
        "reject_inbound_request",
        "Proposer de rejeter une demande entrante, avec un motif.",
        _obj({"source_id": STR, "reason": STR}, ["source_id", "reason"]),
        "write",
        describe=lambda a: {
            "title": f"Rejeter la demande {a.get('source_id')}",
            "impact": [f"Motif : {a.get('reason')}"],
            "effect": "La demande sort de la boîte IA avec le statut Rejeté.",
        },
    ),
]

READ_TOOLS = [
    Tool(
        "search_customers",
        "Chercher des clients par nom ou courriel.",
        _obj({"query": STR}, ["query"]),
        "read",
        _search_customers,
    ),
    Tool(
        "get_customer",
        "Fiche 360° d'un client : locations, factures, paiements, assurance.",
        _obj({"customer": STR}, ["customer"]),
        "read",
        _get_customer,
    ),
    Tool(
        "search_equipment",
        "Chercher des équipements du catalogue locatif.",
        _obj({"query": STR, "category": STR}),
        "read",
        _search_equipment,
    ),
    Tool(
        "get_equipment",
        "Fiche d'un équipement : tarif, valeur, flotte, courbe de prix.",
        _obj({"item_code": STR}, ["item_code"]),
        "read",
        _get_equipment,
    ),
    Tool(
        "check_availability",
        "Vérifier la disponibilité réelle d'articles sur une période.",
        _obj({"items": ITEMS, "starts_at": DATETIME, "ends_at": DATETIME}, ["items", "starts_at", "ends_at"]),
        "read",
        _check_availability,
    ),
    Tool(
        "preview_price",
        "Calculer le prix serveur d'articles sur une période (jours facturables, taxes estimées).",
        _obj({"items": ITEMS, "starts_at": DATETIME, "ends_at": DATETIME}, ["items", "starts_at", "ends_at"]),
        "read",
        _preview_price,
    ),
    Tool(
        "list_rentals",
        "Lister les locations (état : Quote, Reservation, Contract, Checked Out, Returned, Closed, Cancelled, Disputed).",
        _obj({"state": STR, "search": STR, "starts_from": DATE, "starts_to": DATE}),
        "read",
        _list_rentals,
    ),
    Tool("get_rental", "Détail complet d'une location.", _obj({"rental": STR}, ["rental"]), "read", _get_rental),
    Tool(
        "operations_overview",
        "Aperçu opérationnel d'une journée : départs, retours, retards, exceptions.",
        _obj({"day": DATE}),
        "read",
        _operations_overview,
    ),
    Tool(
        "profit_and_loss",
        "Compte de résultat ERPNext sur une période.",
        _obj(
            {
                "from_date": DATE,
                "to_date": DATE,
                "periodicity": {"type": "string", "enum": ["Monthly", "Quarterly", "Half-Yearly", "Yearly"]},
            },
            ["from_date", "to_date"],
        ),
        "read",
        _profit_and_loss,
        roles=FINANCE_ROLES,
    ),
    Tool(
        "list_invoices",
        "Lister les factures de location (statut : Unpaid, Overdue, Paid, Partly Paid, Draft).",
        _obj({"status": STR, "search": STR}),
        "read",
        _list_invoices,
        roles=FINANCE_ROLES,
    ),
    Tool(
        "rental_billing",
        "Situation de facturation d'une location : acompte, paiements, facture de solde.",
        _obj({"rental": STR}, ["rental"]),
        "read",
        _rental_billing,
    ),
    Tool(
        "consignment_dashboard",
        "Tableau de bord de consignation pour un mois (AAAA-MM).",
        _obj({"period": STR}),
        "read",
        _consignment_dashboard,
    ),
    Tool(
        "owner_statement",
        "Relevé d'un propriétaire en consignation pour un mois (AAAA-MM).",
        _obj({"owner": STR, "period": STR}, ["owner", "period"]),
        "read",
        _owner_statement,
    ),
    Tool(
        "ai_inbox",
        "Éléments à traiter : approbations, demandes entrantes, brouillons d'agents.",
        _obj({"kind": {"type": "string", "enum": ["approval", "inbound", "draft"]}}),
        "read",
        _ai_inbox,
    ),
    Tool(
        "pricing_policies",
        "Grille des jours facturables et paramètres de facturation de la société.",
        _obj({}),
        "read",
        _pricing_policies,
    ),
    Tool(
        "open_page",
        "Proposer un lien vers une page Cortex (ex. /rentals/CR-TRX-0001, /availability, /finance/invoices).",
        _obj({"route": STR, "label": STR}, ["route", "label"]),
        "ui",
        _open_page,
    ),
]

TOOLS: Dict[str, Tool] = {tool.name: tool for tool in READ_TOOLS + WRITE_TOOLS}


def tools_for(roles: set) -> List[Tool]:
    """Tools offered to this person (admins see everything; endpoints still enforce)."""
    admin = bool(roles & {"System Manager", "Cortex System Manager", "Administrator"})
    return [t for t in TOOLS.values() if admin or not t.roles or roles & t.roles]
