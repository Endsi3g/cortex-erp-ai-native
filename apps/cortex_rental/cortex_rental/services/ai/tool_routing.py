"""Choix des outils offerts au modèle pour les PETITS modèles (profil « compact » : Gemma 4 par l'API Gemini ou en local).

Pourquoi : chaque tour envoie au modèle les déclarations de TOUS ses outils (26 ici, ~5 000 jetons avec les consignes). Sur
un petit modèle ou un processeur, c'est la différence entre quelques secondes et plusieurs minutes, et plus il y a d'outils,
plus il s'en trompe. On n'offre donc que ceux que la demande évoque, choisis **sans modèle** par des mots-clés (déterministe :
aucun jeton de plus, résultat prévisible, testable).

Règles de sécurité :
- ne rend que des outils déjà permis par la politique de l'agent (`allowed`), jamais un outil de plus;
- un outil qui PROPOSE une écriture n'est offert que si la demande contient un verbe d'action ET évoque son sujet; les outils de
  lecture dont il a besoin l'accompagnent (retrouver l'identifiant exact);
- sans aucun indice, un petit jeu de lectures sûres (jamais d'écriture).
"""

import re
import unicodedata
from typing import Dict, Iterable, List, Sequence, Tuple

MAX_TOOLS = 9
DEFAULT_READS = ("list_rentals", "search_rental_items", "finance_summary", "find_records")

# Sujet → (mots-clés, outils de lecture)
READ_TOPICS: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {
    "locations": (
        ("location", "devis", "reserv", "contrat", "sortie", "retour", "retard", "retenue", "projet"),
        ("list_rentals", "late_returns", "rentals_by_state", "find_records", "get_record"),
    ),
    "parc": (
        ("disponib", "libre", "stock", "equipement", "catalogue", "parc", "tarif", "prix", "camera", "article"),
        ("search_rental_items", "check_inventory_availability", "find_records", "get_record"),
    ),
    "clients": (("client", "customer", "contact"), ("search_customers", "customer_summary", "find_records")),
    "finance": (
        (
            "factur",
            "paiement",
            "paye",
            "encaiss",
            "finance",
            "chiffre",
            "revenu",
            "taxe",
            "solde",
            "statistique",
            "situation",
        ),
        ("finance_summary", "finance_trend", "list_invoices", "rentals_by_state"),
    ),
    "approbations": (("approb", "autoris", "refus"), ("list_pending_approvals",)),
}

ACTION_VERBS = (
    "cre", "ajout", "nouveau", "nouvelle", "modifi", "chang", "mets", "met ", "remplac", "corrig", "passe", "fais", "fait ",
    "prepar", "genere", "etabli", "libere", "renouvel", "prolong", "reserv", "enregistr", "approuv", "refus", "rejet",
    "applique", "supprim", "retir", "annul", "inscri", "a paye", "ont paye", "vient de", "recu", "payer",
)  # fmt: skip

# Outil qui propose → (mots-clés du sujet, verbes qui le déclenchent, outils de lecture qui l'accompagnent). Le verbe compte :
# « réserve le devis » veut réserver, pas créer un devis.
CREATE = ("cre", "ajout", "nouveau", "nouvelle", "prepar", "fais", "genere", "etabli")
ACTION_TOPICS: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]] = {
    "propose_create_customer": (("client",), CREATE, ("search_customers",)),
    "propose_create_quote": (("devis",), CREATE, ("search_customers", "search_rental_items", "check_inventory_availability")),
    "propose_release_hold": (("retenue",), ("libere", "annul", "retir"), ("list_rentals",)),
    "propose_renew_hold": (("retenue",), ("renouvel", "prolong"), ("list_rentals",)),
    "propose_request_reservation": (("reserv", "devis"), ("reserv", "transforme"), ("list_rentals",)),
    "propose_record_payment": (
        ("paiement", "paye", "recu", "cheque", "virement", "encaiss", "factur"),
        ("paye", "payer", "recu", "enregistr", "encaiss", "vient de"),
        ("list_invoices",),
    ),
    "propose_decide_approval": (("approb", "approuv", "refus", "rejet", "demande"), ("approuv", "refus", "rejet"), ("list_pending_approvals",)),
    "propose_update_field": (
        ("tarif", "prix", "nom", "note", "depot", "acompte", "valeur", "parametre", "reglage", "champ", "site", "telephone", "courriel"),
        ("modifi", "chang", "mets", "met ", "remplac", "corrig", "passe", "fais"),
        ("find_records", "get_record"),
    ),
    "propose_apply_sector_template": (("modele", "secteur"), ("applique", "install", "mets", "utilis"), ()),
    "propose_add_category": (("categorie",), ("ajout", "cre", "nouvelle"), ()),
    "propose_add_section": (("section",), ("ajout", "cre", "nouvelle"), ()),
    "propose_add_custom_field": (("champ",), ("ajout", "cre", "nouveau"), ()),
    "propose_add_workspace_shortcut": (("raccourci",), ("ajout", "cre", "nouveau"), ("find_records",)),
}  # fmt: skip


def plain(text: str) -> str:
    """Pur : minuscules sans accents, pour comparer des mots-clés."""
    return "".join(c for c in unicodedata.normalize("NFD", (text or "").lower()) if unicodedata.category(c) != "Mn")


def _starts(text: str, word: str) -> bool:
    """Le mot-clé commence un mot du texte (« nouvelle » ne se trouve pas dans « renouvelle »)."""
    return re.search(r"(?<![a-z0-9])" + re.escape(word.strip()), text) is not None


def _hits(text: str, words: Iterable[str]) -> bool:
    return any(_starts(text, w) for w in words)


def select_tools(message: str, allowed: Sequence[str], previous: str = "") -> List[str]:
    """Pur : les noms d'outils à offrir, dans l'ordre de `allowed`, jamais plus de MAX_TOOLS, jamais hors de `allowed`.

    `previous` : la demande précédente de la personne, pour « oui, fais-le » qui n'a aucun mot-clé.
    Demande d'action : la ou les propositions les mieux appariées (au plus deux) + les lectures qui les accompagnent seulement.
    Demande de lecture : les outils des sujets évoqués."""
    text = plain(f"{previous} {message}")
    now = plain(message)
    topical = tuple(k for words, _ in READ_TOPICS.values() for k in words)
    acting = _hits(now, ACTION_VERBS) or (not _hits(now, topical) and _hits(text, ACTION_VERBS))
    chosen: List[str] = []

    def add(names: Iterable[str]) -> None:
        for name in names:
            if name in allowed and name not in chosen:
                chosen.append(name)

    scored = []
    if acting:
        for tool, (words, verbs, reads) in ACTION_TOPICS.items():
            score = sum(1 for w in words if _starts(text, w))
            if score and _hits(text, verbs) and tool in allowed:
                scored.append((score, tool, reads))
    if scored:
        best = max(score for score, _, _ in scored)
        for _, tool, reads in [t for t in scored if t[0] == best][:2]:
            add(reads)
            add([tool])
    else:
        for words, reads in READ_TOPICS.values():
            if _hits(text, words):
                add(reads)
    if not chosen:
        add(DEFAULT_READS)
    ordered = [n for n in allowed if n in chosen]
    reads = [n for n in ordered if not n.startswith("propose_")]
    writes = [n for n in ordered if n.startswith("propose_")]
    return (reads[: max(MAX_TOOLS - len(writes), 3)] + writes)[:MAX_TOOLS]
