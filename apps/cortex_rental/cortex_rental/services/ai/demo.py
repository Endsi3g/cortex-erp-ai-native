"""Mode démonstration de l'assistant : sans modèle IA, mais avec de VRAIES données et sans rien prétendre.

Utilisé seulement quand aucune clé de modèle n'est configurée. Il comprend quatre demandes (disponibilité, retours en
retard, approbations en attente, catalogue) et répond avec les chiffres du serveur; toute autre question reçoit une
réponse franche. Aucun nombre n'est inventé (pas de jetons fictifs, aucune « vérification » qui n'a pas eu lieu), et
toute réponse porte l'étiquette « démonstration » côté interface (voir api/v1/chat.status)."""

import re
import unicodedata
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    import frappe
    from frappe.utils import getdate, now_datetime, today
except ImportError:
    frappe = None

PROVIDER = "demo"
MODEL = "demo"
HELP = (
    "Je suis en mode démonstration : aucun modèle d'IA n'est configuré, donc je ne comprends que quatre demandes. "
    "Demandez-moi la disponibilité du parc, les retours en retard, les approbations en attente ou le catalogue. "
    "Avec un modèle configuré, je répondrai librement à toutes vos questions."
)
ACTIONS = {
    "cortex.rental_transaction.transition_to_contract": "Confirmer un contrat",
    "cortex.rental_transaction.transition_to_reservation": "Confirmer une réservation",
}
INTENTS = (
    ("late", ("retard",)),
    ("approvals", ("approbation", "valider", "decision", "attente")),
    ("availability", ("dispo", "libre", "creneau", "inventaire", "conflit", "parc")),
    (
        "catalog",
        ("devis", "soumission", "catalogue", "equipement", "louer", "location", "tarif", "prix", "camera", "cout"),
    ),
)
MONTHS = (
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
)
STOPWORDS = {"combien", "coute", "cout", "location", "louer", "pour", "une", "des", "les", "quel", "quels", "quelle"}
MAX_LINES = 12


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower()


def detect(message: str) -> str:
    low = normalize(message)
    for name, words in INTENTS:
        if any(w in low for w in words):
            return name
    return "help"


def parse_period(message: str, today_: Optional[date] = None) -> Optional[Tuple[date, date]]:
    """« du 20 au 22 octobre », « le 5 novembre », « 30 jours » → (début, fin). None si rien de précis n'est demandé.

    Le mode démonstration ne devine pas : une date qu'il ne comprend pas ne devient jamais une autre période."""
    low = normalize(message)
    today_ = today_ or _today()
    month = "|".join(MONTHS)
    match = re.search(rf"\b(\d{{1,2}})\s*(?:er)?\s*(?:au|a|-)\s*(\d{{1,2}})\s+({month})\b", low)
    first = last = None
    if match:
        first, last, name = int(match.group(1)), int(match.group(2)), match.group(3)
        start_month = end_month = MONTHS.index(name) + 1
    else:
        match = re.search(rf"\b(\d{{1,2}})\s*(?:er)?\s+({month})\b", low)
        if match:
            first = last = int(match.group(1))
            start_month = end_month = MONTHS.index(match.group(2)) + 1
    if first is not None:
        year = today_.year
        try:
            start = date(year, start_month, first)
            end = date(year, end_month, last)
            if end < today_:
                start, end = date(year + 1, start_month, first), date(year + 1, end_month, last)
        except ValueError:
            return None
        return (start, end) if end >= start else None
    if re.search(r"\b30\s*jours\b|\bun mois\b|\bce mois\b", low):
        return today_, today_ + timedelta(days=29)
    return None


_MONTHS_SHORT = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juill.", "août", "sept.", "oct.", "nov.", "déc.")


def _fr_date(value: date) -> str:
    """20 oct. 2026 : la date dans le format du Québec, jamais l'ISO brut."""
    return f"{value.day} {_MONTHS_SHORT[value.month - 1]} {value.year}"


def _today() -> date:
    return getdate(today()) if frappe else date.today()


def _people(users: List[str]) -> Dict[str, str]:
    return {u: (frappe.utils.get_fullname(u) if frappe else u) or u for u in set(users)}


def _more(items: List[str], total: int) -> List[str]:
    return items + (
        [f"… et {total - len(items)} autre(s) : ouvrez la grille complète pour tout voir."]
        if total > len(items)
        else []
    )


def money(value: Any) -> str:
    """Montant au format français : 1 234,50 $."""
    text = f"{float(value or 0):,.2f}".replace(",", " ").replace(".", ",")
    return f"{text} $"


def _fact(title: str, items: List[str], source_ids: List[str]) -> Dict[str, Any]:
    return {
        "type": "verified_fact",
        "title": title,
        "items": items,
        "source_ids": source_ids,
        "checked_at": str(now_datetime())[:19],
    }


def _action(action: str, title: str) -> Dict[str, Any]:
    """Bouton d'action discret sous une réponse : il ouvre un questionnaire, il ne crée rien."""
    return {
        "type": "proposal",
        "title": title,
        "summary": "",
        "impact": [],
        "action": action,
        "requires_approval": False,
    }


def _progress(label: str) -> Dict[str, Any]:
    return {"type": "tool_progress", "tool_name": label, "state": "success", "message": ""}


def _text(text: str) -> Dict[str, Any]:
    return {"type": "assistant_text", "text": text, "source_ids": []}


def _answer(message: str) -> Dict[str, Any]:
    """Retourne {text, blocks, tool_calls} pour la demande, d'après les outils sous les droits de la personne connectée."""
    from cortex_rental.permissions.agent_scopes import get_company_context
    from cortex_rental.services import availability_summary
    from cortex_rental.services.ai import tools

    intent = detect(message)
    if intent == "help":
        return {"text": HELP, "blocks": [_text(HELP)], "tool_calls": []}

    if intent == "late":
        rows = tools.late_returns(limit=10).get("late", [])
        if rows:
            now = now_datetime()
            items = [
                f"{r['name']} · {r['customer']} · devait revenir le {str(r['ends_at'])[:10]} "
                f"({max((now - frappe.utils.get_datetime(r['ends_at'])).days, 0)} j de retard)"
                for r in rows
            ]
            text = f"{len(rows)} location(s) en retard de retour."
        else:
            items, text = ["Aucun retour en retard."], "Aucun retour en retard pour le moment."
        return {
            "text": text,
            "blocks": [
                _progress("Recherche des retours en retard"),
                _text(text),
                _fact("Retours en retard", items, [r["name"] for r in rows]),
            ],
            "tool_calls": ["late_returns"],
        }

    if intent == "approvals":
        rows = tools.list_pending_approvals(limit=10).get("pending", [])
        if rows:
            names = _people([r["requested_by_id"] for r in rows])
            items = [
                f"{ACTIONS.get(r['action'], 'Décision requise')} · {r['entity_id']} · "
                f"demandée par {names[r['requested_by_id']]} le {str(r['creation'])[:10]}"
                for r in rows
            ]
            text = f"{len(rows)} demande(s) d'approbation attendent une décision humaine."
        else:
            items, text = ["Aucune demande en attente."], "Aucune demande d'approbation en attente."
        blocks = [
            _progress("Consultation des approbations"),
            _text(text),
            _fact("Approbations en attente", items, [r["name"] for r in rows]),
        ]
        if rows:
            blocks.append(_action("open_approvals_flow", "Examiner les demandes"))
        return {"text": text, "blocks": blocks, "tool_calls": ["list_pending_approvals"]}

    if intent == "availability":
        from cortex_rental.api.v1.availability import get_matrix_handler

        period = parse_period(message)
        first, last = period or (_today(), _today() + timedelta(days=6))
        start, end = str(first), str(last)
        if (last - first).days + 1 > availability_summary.MAX_DAYS:
            text = f"La période dépasse {availability_summary.MAX_DAYS} jours : choisissez une période plus courte."
            return {"text": text, "blocks": [_text(text)], "tool_calls": []}
        matrix = get_matrix_handler(payload={"starts_at": start, "ends_at": end}, company=get_company_context())
        rows = availability_summary.summarize(matrix.get("items", []), start, end, now_datetime())
        labels = {"ok": "libre", "partial": "partiellement pris", "full": "complet", "none": "aucun au parc"}
        lines = [
            f"{r['item_name']} : {r['free']:g} libre(s) au pire jour sur {r['fleet']:g} ({labels[r['status']]})"
            for r in rows[:MAX_LINES]
        ]
        busy = sum(1 for r in rows if r["status"] in ("partial", "full"))
        label = f"du {_fr_date(first)} au {_fr_date(last)}" if period else "des 7 prochains jours"
        text = f"Du {_fr_date(first)} au {_fr_date(last)} : {busy} équipement(s) sur {len(rows)} ont des réservations ou retenues."
        if not period and re.search(r"\d", message):
            text += " Je n'ai pas compris la période demandée : voici les 7 prochains jours. Utilisez le questionnaire « Grille de disponibilité » pour choisir vos dates."
        blocks = [
            _progress("Vérification de la disponibilité"),
            _text(text),
            _fact(
                f"Disponibilité {label}",
                _more(lines, len(rows)) or ["Aucun équipement au catalogue."],
                [r["item_code"] for r in rows[:MAX_LINES]],
            ),
            _action("open_availability_flow", "Choisir une autre période"),
            _action("open_quote_composer", "Préparer un devis"),
        ]
        return {"text": text, "blocks": blocks, "tool_calls": ["check_inventory_availability"]}

    words = [w for w in dict.fromkeys(re.findall(r"[a-z0-9]{3,}", normalize(message))) if w not in STOPWORDS][:4]
    found: Dict[str, Dict[str, Any]] = {}
    for word in words:
        for row in tools.search_rental_items(query=word).get("items", []):
            found.setdefault(row["item_code"], row)
    # Les articles qui contiennent le plus de mots de la demande passent en premier.
    ranked = sorted(
        found.values(),
        key=lambda r: -sum(1 for w in words if w in normalize(r["item_name"] + " " + r["item_code"])),
    )
    shown = ranked or tools.search_rental_items(query="").get("items", [])
    rows = shown[:MAX_LINES]
    lines = [
        f"{r['item_name']} ({r['item_code']}) : {money(r.get('daily_rate'))} par jour, {r.get('total_quantity', 1):g} au parc"
        for r in rows
    ]
    asked_price = any(w in normalize(message) for w in ("prix", "cout", "combien", "tarif"))
    text = (
        "Je ne calcule pas de prix en mode démonstration : voici les tarifs journaliers. "
        "Pour un prix exact (règles de durée comprises), utilisez le questionnaire « Nouvelle location »."
        if asked_price
        else "Voici votre catalogue de location."
    )
    blocks: List[Dict[str, Any]] = [
        _progress("Recherche dans le catalogue"),
        _text(text),
        _fact(
            "Catalogue et tarifs",
            _more(lines, len(shown)) or ["Aucun équipement au catalogue de cette société."],
            [r["item_code"] for r in rows],
        ),
    ]
    if rows:
        blocks.append(_action("open_quote_composer", "Préparer un devis"))
    return {"text": text, "blocks": blocks, "tool_calls": ["search_rental_items"]}


def answer(message: str) -> Dict[str, Any]:
    """Réponse de démonstration ; un refus de droits devient une phrase claire, jamais une erreur technique."""
    try:
        return _answer(message)
    except Exception as exc:  # noqa: BLE001
        if frappe and isinstance(exc, frappe.PermissionError):
            text = "Votre rôle ne permet pas de consulter cette information. Demandez l'accès à un administrateur."
            return {"text": text, "blocks": [_text(text)], "tool_calls": []}
        raise
