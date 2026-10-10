"""Cartes de statistiques de l'assistant : des chiffres réels de la société, jamais estimés, avec un lien vers la source.

Les fonctions pures (`monthly_totals`, `safe_href`, `money`, `kpi_block`, `series_block`) sont testées sans banc Frappe; les
lectures passent par `frappe.get_list` (droits et société de la personne connectée).
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Seuls les chemins du Desk Cortex sont permis comme destination : jamais un lien externe ni un schéma exotique.
HREF_RE = re.compile(r"^/app/[a-z0-9][a-z0-9\-]{0,60}(/[A-Za-z0-9_%.\-]{1,160}){0,2}(\?[A-Za-z0-9_=%&.\-]{0,200})?$")
# États d'une location (ordre du cycle) et libellés français.
STATE_ORDER = [
    "Quote",
    "Reservation",
    "Contract",
    "Checked Out",
    "Partially Returned",
    "Returned",
    "Closed",
    "Disputed",
    "Cancelled",
]
STATE_LABELS = {
    "Quote": "Devis",
    "Reservation": "Réservation",
    "Contract": "Contrat",
    "Checked Out": "Sortie",
    "Partially Returned": "Retour partiel",
    "Returned": "Retournée",
    "Closed": "Clôturée",
    "Disputed": "Litige",
    "Cancelled": "Annulée",
}
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juill.", "août", "sept.", "oct.", "nov.", "déc."]


def safe_href(href: Any) -> str:
    """Pur : le chemin du Desk s'il est sûr, sinon une chaîne vide (la carte n'affiche alors aucune flèche)."""
    text = str(href or "").strip()
    return text if HREF_RE.match(text) and ".." not in text else ""


def money(value: Any) -> str:
    """Pur : « 1 234,50 $ » (format canadien-français)."""
    amount = float(value or 0)
    whole, _, cents = f"{abs(amount):,.2f}".partition(".")
    text = f"{whole.replace(',', ' ')},{cents} $"  # espace insécable fine entre les milliers
    return f"-{text}" if amount < 0 else text


def human_dt(value: Any) -> str:
    """Pur : « 14 oct. 2026, 09 h 00 » à partir de « AAAA-MM-JJ hh:mm… »; le texte d'origine si le format est inattendu."""
    text = str(value or "").strip()
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})", text)
    if not match:
        return text
    year, month, day, hour, minute = (int(g) for g in match.groups())
    if not 1 <= month <= 12:
        return text
    return f"{day} {MONTHS[month - 1]} {year}, {hour:02d} h {minute:02d}"


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def last_months(today: Tuple[int, int, int], count: int) -> List[Tuple[int, int]]:
    """Pur : les `count` derniers mois (année, mois), du plus ancien au courant."""
    year, month = today[0], today[1]
    out = []
    for _ in range(max(1, min(count, 24))):
        out.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(out))


def monthly_totals(
    rows: Iterable[Dict[str, Any]], today: Tuple[int, int, int], count: int, field: str, date_field: str
):
    """Pur : somme de `field` par mois, avec 0 pour un mois sans données (le mois courant est partiel, à dire)."""
    months = last_months(today, count)
    totals = {month_key(y, m): 0.0 for y, m in months}
    for row in rows:
        key = str(row.get(date_field) or "")[:7]
        if key in totals:
            totals[key] += float(row.get(field) or 0)
    labels = [f"{MONTHS[m - 1]} {y}" if m == 1 or i == 0 else MONTHS[m - 1] for i, (y, m) in enumerate(months)]
    return labels, [round(totals[month_key(y, m)], 2) for y, m in months]


def kpi_block(label: str, value: str, detail: str = "", tone: str = "neutral") -> Dict[str, Any]:
    return {"label": label, "value": value, "detail": detail or None, "tone": tone}


def series_block(kind: str, labels: List[str], values: List[float], unit: str = "") -> Dict[str, Any]:
    return {"kind": kind, "labels": list(labels), "values": [float(v) for v in values], "unit": unit}


def card(
    title: str,
    source_label: str,
    source_href: str,
    *,
    subtitle: str = "",
    kpis: Optional[List[Dict[str, Any]]] = None,
    series: Optional[Dict[str, Any]] = None,
    checked_at: str = "",
) -> Dict[str, Any]:
    """Pur : le bloc `stat_card`; un lien non sûr est retiré (la carte reste, sans flèche)."""
    return {
        "type": "stat_card",
        "title": title,
        "subtitle": subtitle or None,
        "kpis": kpis or [],
        "series": series,
        "source_label": source_label,
        "source_href": safe_href(source_href),
        "checked_at": checked_at or None,
    }
